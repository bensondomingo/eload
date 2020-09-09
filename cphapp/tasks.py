from __future__ import absolute_import, unicode_literals
import json
import logging
from requests.exceptions import ConnectionError

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import ValidationError

from cphapp.models import LoadTransaction
from cphapp.api.serializers import LoadTransactionSerializer
from cphapp import redis
from cph.coinsph import (
    fetch_crypto_payment, fetch_orders, request_new_order as rno)

from celery import shared_task
from celery.result import AsyncResult
from celery.app.task import Task
from django_celery_beat.models import PeriodicTask

from cphapp import utility
from cphapp import exceptions
from cphapp.test_assets import defines, json_file_path

logger = logging.getLogger(__name__)

# IDs used in redis db 1
TASK_ID_ONGOING_SYNC = 'task.id.ongoing.sync'
TASK_ID_PENDING_ORDERS = 'task.id.pending.orders'

USER_MODEL = get_user_model()


class RequestNewOrderTask(Task):

    def on_success(self, retval, task_id, args, kwargs):
        # Start update_order_data task
        transaction_id = kwargs.get('transaction_id')
        retval.update({
            'transaction_id': transaction_id,
            'transaction_type': 'sellorder'})

        s = LoadTransactionSerializer(data=retval)
        if not s.is_valid():
            logger.error(s.errors)
            raise ValidationError(s.error_messages)
        s.save()

        logger.info('Load order %s successfully created', transaction_id)
        logger.info('Running update_order_data task ...')
        AsyncResult(task_id).forget()
        update_order_data.apply(kwargs={'id': transaction_id})

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        transaction_id = kwargs.get('transaction_id')
        if isinstance(exc, exceptions.RequestNewOrderError):
            error = ', '.join(exc.errors)
        else:
            error = exc.__str__()
        logger.error('An error occured %s: %s', transaction_id, error)
        obj = LoadTransaction.objects.get(id=transaction_id)
        obj.error = error
        obj.save()
        return super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(
    bind=True, base=RequestNewOrderTask,
    autoretry_for=(ConnectionError,),
    retry_kwargs={'max_retries': 10},
    retry_backoff=True)
def request_new_order(self, transaction_id, data):
    """
    Fire a new POST request to 3rd party endpoint initiating buy of load.
    """
    if transaction_id in defines.TEST_ORDER_IDS:
        logger.info('request_new_order in TEST mode, using %s',
                    json_file_path.POST_REQUEST_RESP_JSON)
        with open(json_file_path.POST_REQUEST_RESP_JSON, 'r') as f:
            resp = json.load(f)
    else:
        logger.info(
            'request_new_order in PROD mode, request new order %s', data)
        resp = rno(data)
        if resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            raise exceptions.RequestNewOrderError(data, resp.json())
        resp = resp.json()
    return resp.get('order')


class UpdateOrderDataTask(Task):

    def on_success(self, retval, task_id, args, kwargs):
        # retval['model_id'] = kwargs.get('id')
        AsyncResult(id=task_id).forget()

        order_status = retval.get('delivery_status')
        update_payment_data.apply(
            kwargs={'order_id': retval.get('id'),
                    'order_status': order_status})

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        return super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(
    bind=True, base=UpdateOrderDataTask,
    autoretry_for=(Exception, ),
    retry_backoff=True)
def update_order_data(self, id):
    if id in defines.TEST_ORDER_IDS:
        logger.info('update_order_data in TEST mode, using %s',
                    json_file_path.GET_REQUEST_RESP_JSON)
        with open(json_file_path.GET_REQUEST_RESP_JSON, 'r') as f:
            resp = json.load(f)
            order = resp.get('orders')[0]
    else:
        logger.info('update_order_data in PROD mode, fetch new data')
        resp = fetch_orders(order_type='sellorder', external_transaction_id=id)
        order = resp.json().get('orders')[0]

    order_status = order.get('delivery_status')
    if order_status not in ['settled', 'refunded', 'expired']:
        e = exceptions.OrderStatusError(order_status, id)
        logger.error(e.__str__())
        raise e
    logger.info('Order %s status already finalized.', id)
    return order


class UpdatePaymentTask(Task):

    def on_success(self, retval, task_id, args, kwargs):
        order_id = kwargs.get('order_id')
        logger.info(order_id)
        try:
            obj = LoadTransaction.objects.get(order_id=kwargs.get('order_id'))
        except LoadTransaction.MultipleObjectsReturned as e:
            logger.error(order_id)
            raise e

        order_status = kwargs.get('order_status')
        if order_status is not None:
            retval.update({'status': order_status})

        s = LoadTransactionSerializer(obj, data=retval, partial=True)
        if not s.is_valid():
            logger.critical(s.errors)
        obj = s.update(obj, s.validated_data)

        # Clear result from result backend
        logger.info('Clearing task %s result from result backend.',
                    self.request.id)
        AsyncResult(task_id).forget()
        logger.info('Task %s succeeded', self.request.id)


@shared_task(bind=True, base=UpdatePaymentTask,
             autoretry_for=(Exception,),
             retry_backoff=True)
def update_payment_data(self, order_id, order_status=None):
    try:
        response = fetch_crypto_payment(order_id)
    except ConnectionError as e:
        logger.exception("Something wen't wrong with the connection while "
                         "fetching payment data of transaction %s", order_id)
        raise e
    except AssertionError as e:
        logger.exception('An unexpected status code received from server '
                         'while fetching payment data of transaction %s',
                         order_id)
        raise e
    except Exception as e:
        logger.exception('An unknown error has occured while fetching '
                         'payment data of transaction %s', order_id)
        raise e

    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        logger.error(
            'Encountered error HTTP_429_TOO_MANY_REQUESTS. order_id: %s',
            order_id)
        raise exceptions.CryptoPaymentThrottlingError(order_id=order_id)
    payment = response.json().get('crypto-payments')[0]

    return {
        'posted_amount': payment.get('posted_amount'),
        'running_balance': payment.get('running_balance')
    }


@shared_task(ignore_result=True)
def sync_order_db():
    try:
        ongoing_sync = redis.get(TASK_ID_ONGOING_SYNC).decode()
        logger.info('ONGOING_SYNC: %s', ongoing_sync)
        if ongoing_sync == 'TRUE':
            logger.info("There's an ongoing sync. Retry later.")
            return
    except AttributeError:
        redis.set(TASK_ID_ONGOING_SYNC, 'FALSE')
        return

    logger.info('Synchronizing DB')
    redis.set(TASK_ID_ONGOING_SYNC, 'TRUE')
    try:
        utility.sync_order_db('sellorder')
        utility.sync_order_db('buyorder')

        logger.info('Sync DONE')
    except Exception as e:
        logger.exception(e.__str__())
    finally:
        redis.set(TASK_ID_ONGOING_SYNC, 'FALSE')


@shared_task(ignore_result=True)
def check_pending_orders():
    logger.info('Checking pending orders')
    periodic_sync_db = PeriodicTask.objects.get(name='sync_db')
    enabled = periodic_sync_db.enabled
    pending_count = redis.llen(TASK_ID_PENDING_ORDERS)
    logger.info('Pending order count %s. sync_order_db task %s',
                pending_count, 'enabled' if enabled else 'disabled')
    if pending_count == 0 and enabled:
        periodic_sync_db.enabled = False
        logger.info('Disabling sync_order_db task')
        periodic_sync_db.save()
    elif pending_count == 1 and not enabled:
        periodic_sync_db.enabled = True
        logger.info('Enabling sync_order_db task')
        periodic_sync_db.save()
        sync_order_db.delay()
