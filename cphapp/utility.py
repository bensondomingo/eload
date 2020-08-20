import logging

from rest_framework import status
from rest_framework import serializers

from cphapp.models import LoadTransaction as Order, LoadOutlet
from cphapp.api.serializers import LoadTransactionSerializer, LoadOutletSerializer
from cph import coinsph

logger = logging.getLogger(__name__)


def fetch_orders(order_type, count, offset=0):
    orders = []
    limit = count if count <= 100 else 100
    remaining = count - limit
    resp = coinsph.fetch_orders(
        order_type, limit=limit, offset=offset, status='success')
    orders += resp.get('orders')
    if remaining == 0:
        return orders
    else:
        orders += fetch_orders(order_type, remaining, offset=offset + limit)
    return orders


def sync_order_db(order_type):
    num_instance_in_db = Order.objects.filter(
        transaction_type=order_type).count()
    resp = coinsph.fetch_orders(order_type, limit=1)
    current_count = resp.get('meta').get('pagination').get('total')
    if current_count == num_instance_in_db:
        return

    diff_count = current_count - num_instance_in_db
    logger.info('Fetch and sync %d new transactions', diff_count)
    orders = fetch_orders(order_type, diff_count)

    for order in orders:
        order['transaction_type'] = order_type
        serializer = LoadTransactionSerializer(data=order)
        if not serializer.is_valid():
            logger.error('Error while serializing %s with ID %s. %s.',
                         order_type, order.get('id'),
                         serializer.error_messages)
            logger.error(serializer.initial_data)
        else:
            serializer.create(serializer.validated_data)


def update_outlet_data(phone_number):
    try:
        resp = coinsph.fetch_outlet_data(phone_number)
    except Exception as e:
        logger.exception(
            "Someting wen't wrong while trying to fetch %s outlet data",
            phone_number)
        raise e

    if resp.status_code != status.HTTP_200_OK:
        raise serializers.ValidationError(resp.json())

    resp = resp.json()
    payout_outlet = resp.get('payout-outlets')[0]
    outlet_id = payout_outlet.get('id')
    try:
        outlet = LoadOutlet.objects.get(id=outlet_id)
    except LoadOutlet.DoesNotExist:
        s = LoadOutletSerializer(data=payout_outlet)
        if not s.is_valid():
            pass
        outlet = s.create(s.validated_data)
    finally:
        outlet.phone_number_prefixes.append(phone_number[:6])
        outlet.save()
        return outlet
