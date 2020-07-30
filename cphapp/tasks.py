from __future__ import absolute_import, unicode_literals
import logging
from requests.exceptions import ConnectionError
from re import search as re_search

from django.db.models import Sum
from cphapp.models import Transaction
from cphapp import redis
from cphapp.api.serializers import TransactionSerializer
from cph.coinsph import fetch_crypto_payment, ThrottleError

from celery import shared_task
from celery.result import AsyncResult
from celery.app.task import Task
from django_celery_beat.models import PeriodicTask

from cphapp import utility

logger = logging.getLogger(__name__)

# IDs used in redis db 1
TASK_ID_ONGOING_SYNC = 'task.id.ongoing.sync'
TASK_ID_PENDING_ORDERS = 'task.id.pending.orders'


class UpdateTransactionTask(Task):

    def on_success(self, retval, task_id, args, kwargs):

        data = retval
        transaction = Transaction.objects.get(id=kwargs.get('order_id'))

        if transaction.transaction_type == 'sellorder':
            sold_this_month = Transaction.objects.filter(
                status='settled',
                transaction_date__month=transaction.transaction_date.month,
                transaction_date__year=transaction.transaction_date.year).aggregate(    # noqa: E501
                amount=Sum('amount')).get('amount')
            reward_factor = 0.1 if sold_this_month <= 10e3 else 0.05

            if data.get('posted_amount').startswith('-'):
                # Transaction succeeded if posted_amount (the amount deducted)
                # is a negative number
                reward = transaction.amount * reward_factor
            else:
                reward = 0

            data.update({
                'running_balance': float(data.get('running_balance')) + reward,
                'reward_amount': reward})

        # Update
        serializer = TransactionSerializer(
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


@shared_task(bind=True, base=UpdateTransactionTask)
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
