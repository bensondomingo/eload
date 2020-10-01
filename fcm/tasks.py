import logging

from celery import shared_task
from firebase_admin import messaging
import firebase_admin

from fcm.models import FCMDevice
from eload import fcm_app

from cphapp.models import LoadTransaction
from cphapp.api.serializers import LoadTransactionSerializer
from profiles.models import Profile as Retailer

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def fcm_check_valid_tokens(owner_id):
    for token in FCMDevice.objects.filter(owner__id=owner_id):
        message = messaging.Message(token=token.token)
        try:
            messaging.send(message, dry_run=True, app=fcm_app)
        except messaging.UnregisteredError:
            logger.info('Deleting unregistered token: ', token.token)
            token.delete()


@shared_task(ignore_result=True)
def send_confirmation(order_id):
    """ Send notification confirming transaction result and status """

    try:
        firebase_admin.get_app()
    except ValueError:
        # Just return if there is no initialized firebase app
        return

    obj = LoadTransaction.objects.get(order_id=order_id)
    data = LoadTransactionSerializer(obj).data

    # Get retailer fcm tokens
    retailer = Retailer.objects.get(pk=data.get('retailer'))
    token_qs = retailer.fcmdevices.all()
    if not token_qs.exists():
        logger.info('Unable to send notification for retailer ',
                    retailer.username)
        return

    product_code = data.get('product_code')
    phone_number = data.get('phone_number')

    if product_code == 'regular':
        product = f'P{data.get("amount")} amount of regular load'
    else:
        product = product_code

    if data.get('status') == 'settled':
        title = 'Transaction successful!'
        body = (f'You successfully send {product} to {phone_number}. Thank '
                'you for using LoadNinja.')
        icon = 'notification-success.png'
    else:
        title = 'Transaction failed!'
        body = (f'Your request to send {product} to {phone_number} was '
                'unsuccessful. Please try again later.')
        icon = 'notification-failed.png'

    # Compose notification objects
    wp_notification = messaging.WebpushNotification(
        title=title, body=body,
        icon=f'/static/img/icons/{icon}')
    wp_config = messaging.WebpushConfig(notification=wp_notification)
    # if not settings.DEBUG:
    fcm_options = messaging.WebpushFCMOptions(
        link='https://www.loadninja.xyz')
    wp_config.fcm_options = fcm_options

    tokens = [t.get('token') for t in token_qs.values('token')]
    data = {k: str(v) for k, v in data.items()}
    data['notification_type'] = 'NEW_TRANSACTION'
    messages = messaging.MulticastMessage(tokens, data=data, webpush=wp_config)
    logger.info('Sending notification to retailer %s ...',
                retailer.user.username)
    resp = messaging.send_multicast(messages)
    logger.info('Notification status. Success: %i, Failed: %i',
                resp.success_count, resp.failure_count)
