import logging
from cphapp.models import Transaction as Order
from cphapp.api.serializers import TransactionSerializer
from cph import coinsph

logger = logging.getLogger(__name__)


def fetch_orders(order_type, count, offset=0):
    orders = []
    limit = count if count <= 100 else 100
    remaining = count - limit
    response = coinsph.fetch_orders(
        order_type, limit=limit, offset=offset, status='success')
    orders += response.get('orders')
    if remaining == 0:
        return orders
    else:
        orders += fetch_orders(order_type, remaining, offset=offset + limit)
    return orders


def sync_order_db(order_type):
    num_instance_in_db = Order.objects.filter(
        transaction_type=order_type).count()
    response = coinsph.fetch_orders(order_type, limit=1)
    current_count = response.get('meta').get('pagination').get('total')
    if current_count == num_instance_in_db:
        return

    diff_count = current_count - num_instance_in_db
    logger.info('Fetch and sync %d new transactions', diff_count)
    orders = fetch_orders(order_type, diff_count)

    for order in orders:
        order['transaction_type'] = order_type
        serializer = TransactionSerializer(data=order)
        if not serializer.is_valid():
            logger.error('Error while serializing %s with ID %s. %s.',
                         order_type, order.get('id'),
                         serializer.error_messages)
            logger.error(serializer.initial_data)
        else:
            serializer.create(serializer.validated_data)
