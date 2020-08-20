from __future__ import absolute_import, unicode_literals
import json
import logging
from requests.exceptions import ConnectionError
from re import search as re_search

from rest_framework import status

from cphapp.models import LoadTransaction
from cphapp.api.serializers import LoadTransactionSerializer
from cphapp import redis
from cph.coinsph import (
    fetch_crypto_payment, fetch_orders,
    request_new_order as rno, ThrottleError)

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


class RequestNewOrderTask(Task):

    def _on_success(self, retval, task_id, args, kwargs):
        obj = LoadTransaction.objects.get(id=kwargs.get('transaction_id'))
        s = LoadTransactionSerializer(obj, data=retval, partial=True)
        if not s.is_valid():
            pass
        s.save()
        AsyncResult(task_id).forget()

    def on_success(self, retval, task_id, args, kwargs):
        # Start update_order_data task
        transaction_id = kwargs.get('transaction_id')
        logger.info('Load order %s successfully created', transaction_id)
        logger.info('Running update_order_data task ...')
        update_order_data.apply(kwargs={'id': transaction_id})
        AsyncResult(task_id).forget()
        return super().on_success(retval, task_id, args, kwargs)

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
        obj = LoadTransaction.objects.get(
            id=kwargs.get('id'))
        s = LoadTransactionSerializer(obj, retval, partial=True)
        if not s.is_valid():
            pass
        s.update(obj, s.validated_data)
        AsyncResult(id=task_id).forget()
        update_payment_data.apply_async(kwargs={'order_id': obj.order_id})

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        return super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(
    bind=True, base=UpdateOrderDataTask,
    autoretry_for=(Exception, ),
    retry_backoff=True)
def update_order_data(self, id):
    resp = fetch_orders(order_type='sellorder', external_transaction_id=id)
    order = resp.json().get('orders')[0]
    order_status = order.get('delivery_status')
    if order_status not in ['settled', 'refunded', 'expired']:
        e = exceptions.OrderStatusError(order_status, id)
        logger.error(e.__str__())
        raise e
    logger.info('Order %s status already finalized.', id)
    return order


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
    except Exception:
        print('An error occured during DB sync')
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


class UpdatePaymentTask(Task):

    def on_success(self, retval, task_id, args, kwargs):

        data = retval
        transaction = LoadTransaction.objects.get(
            order_id=kwargs.get('order_id'))

        if transaction.transaction_type == 'sellorder':
            data['running_balance'] = float(
                data.get('running_balance')) + transaction.reward_amount

        # Update
        serializer = LoadTransactionSerializer(
            transaction, partial=True, data=data)
        if not serializer.is_valid():
            logging.critical(serializer.error_messages)
        serializer.save()

        # Clear result from result backend
        logger.info('Clearing task %s result from result backend.',
                    self.request.id)
        AsyncResult(task_id).forget()
        logger.info('Task %s succeeded', self.request.id)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Wait for 30 seconds before firing retry
        self.retry(countdown=30)


@shared_task(bind=True, base=UpdatePaymentTask)
def update_payment_data(self, order_id):
    try:
        response = fetch_crypto_payment(order_id)
    except ConnectionError as e:
        logger.exception("Something wen't wrong with the connection while "
                         "fetching payment data of transaction %s. Will retry "
                         "automatically after 60 seconds", order_id)
        raise e
    except AssertionError as e:
        logger.exception('An unexpected status code received from server '
                         'while fetching payment data of transaction %s. Will '
                         'retry automatically after 60 seconds', order_id)
        raise e
    except Exception as e:
        logger.exception('An unknown error has occured while fetching '
                         'payment data of transaction %s. Will retry '
                         'automatically after 60 seconds', order_id)
        raise e

    try:
        assert(response.get('errors') is None)
    except AssertionError:
        logger.exception(response.get('errors'))
        err_msg = response.get('errors').get('detail')
        pat = r'Request was throttled. Expected available in (\d+) second|s.'
        res = re_search(pat, err_msg)
        try:
            assert(res is not None)
        except AssertionError:
            logger.critical('An unknown error has occured. Please review '
                            'details then write a necessary err handler to '
                            'catch this error.')
            logger.exception('Error')
            return
        else:
            delay = float(res.group(1)) + 2
            logger.error(err_msg)
            logger.info('Retry in %d seconds', delay)
            self.retry(
                countdown=delay, exc=ThrottleError(err_msg))
            return

    payment = response.get('crypto-payments')[0]
    logger.debug(payment)
    return {
        'posted_amount': payment.get('posted_amount'),
        'running_balance': payment.get('running_balance')
    }


class CustomTask(Task):

    def on_success(self, retval, task_id, args, kwargs):
        print('on_success called!')
        print(retval, task_id, args, kwargs)

        res = AsyncResult(task_id)
        print(res.status)
        res.forget()
        print(res.status)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        print('on_retry called!')
        print(exc, task_id, einfo, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        print('on_failure called!')
        print(exc, task_id, einfo)
        print('retry within 5 seconds!')
        self.retry(kwargs={'err': False}, countdown=5)


@shared_task(bind=True, base=CustomTask)
def debug_task(self, err=False):
    from time import sleep
    sleep(1)
    if err:
        raise Exception('Something went wrong')
    return 'debug_task done!'


@shared_task
def logging_task():
    logger.info(logger.name)
    logger.warning(logger.name)
    logger.error(logger.name)
    logger.critical(logger.name)
    try:
        raise Exception('An exception')
    except Exception:
        logger.exception(logger.name)
