import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from cphapp.models import LoadTransaction
from cphapp.tasks import update_payment_data as upd

from cphapp.test_assets import defines

logger = logging.getLogger(__name__)


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
