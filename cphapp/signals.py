import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from cphapp.models import LoadTransaction
from cphapp.tasks import request_new_order as rno, update_payment_data as upd

from cphapp.test_assets import defines

logger = logging.getLogger(__name__)


# @receiver(post_save, sender=LoadTransaction)
def post_eload_data(sender, instance, created, **kwargs):
    """
    Starts a worker that POSTs initial instance data to 3rd party enpoint. This
    is the actual buying of load process. Only called when a retailer/user
    initiates the LoadTransaction create process.

    After the worker successfully returned, the model instance field values
    will be updated with the POST request response data properties.
    """
    if created and instance.confirmation_code is None:
        # TODO: add other relevant retailer properties in the reference field
        data = {
            'amount': instance.amount,
            'currency': 'PHP',
            'payment_outlet': instance.outlet_id,
            'pay_with_wallet': 'PBTC',
            'phone_number_load': instance.phone_number,
            'external_transaction_id': instance.id.hex,
            'reference': {
                "retailer": instance.retailer.username,
                "retailer_email": instance.retailer.email
            }
        }
        if instance.id.hex in defines.TEST_ORDER_IDS:
            # Synchronous in test mode
            rno.apply(kwargs={'transaction_id': instance.id.hex, 'data': data})
        else:
            rno.apply_async(
                kwargs={'transaction_id': instance.id.hex, 'data': data})


@receiver(post_save, sender=LoadTransaction)
def update_payment_data(sender, instance, created, **kwargs):
    """ Purpose is to get balance and posted_amount value """

    if instance.status in ['settled', 'refunded', 'released'] \
            and instance.balance is None:
        logger.info('Fetch payment data for transaction %s', instance.order_id)
        # upd.apply(kwargs={'order_id': instance.order_id})

        if instance.order_id in defines.TEST_ORDER_IDS:
            upd.apply(kwargs={'order_id': instance.order_id})
        else:
            upd.apply_async(kwargs={'order_id': instance.order_id})
