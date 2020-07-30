import logging
from logging import log
from django.db.models.signals import post_save
from django.dispatch import receiver
from cphapp.models import Transaction
from cphapp.tasks import update_payment_data as upd

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def update_payment_data(sender, instance, created, **kwargs):
    if created:
        if instance.status == 'expired' or instance.status == 'canceled':
            return
        logger.debug('Fetch payment data for transaction %s', instance.id)
        upd.apply_async(kwargs={'order_id': instance.id})
