import logging
import json

from requests.exceptions import ConnectionError

from rest_framework import status
from rest_framework import serializers
from rest_framework.response import Response

from cphapp.models import LoadTransaction as Order, LoadOutlet
from cphapp.api.serializers import (
    LoadTransactionSerializer, LoadOutletSerializer)
from cphapp.test_assets import json_file_path

from cph import coinsph

logger = logging.getLogger(__name__)


def fetch_orders(order_type, count, offset=0, test=False):
    max_limit = 10 if test else 100
    limit = count if count <= max_limit else max_limit

    if test:
        if order_type == 'sellorder':
            order_page_list = json_file_path.SELL_ORDER_LIST
        else:
            order_page_list = json_file_path.BUY_ORDER_LIST
        with open(order_page_list[int(offset/max_limit)]) as f:
            orders = json.load(f).get('orders')
    else:
        resp = coinsph.fetch_orders(
            order_type, limit=limit, offset=offset, status='success')
        orders = resp.json().get('orders')

    for order in orders:
        yield order


def sync_order_db(order_type, count=None, offset=0, test=False):
    num_instance_in_db = Order.objects.filter(
        transaction_type=order_type).count()
    if count is None:
        if test:
            if order_type == 'sellorder':
                page1 = json_file_path.GET_REQUEST_SELL_ORDER_LIST_PAGE1
            else:
                page1 = json_file_path.GET_REQUEST_BUY_ORDER_LIST_PAGE1
            with open(page1, 'r') as f:
                resp = Response(json.load(f), status=status.HTTP_200_OK)
                resp = resp.data
        else:
            try:
                resp = coinsph.fetch_orders(order_type, limit=1)
                resp = resp.json()
            except ConnectionError as e:
                logger.exception('Unable to connect to server')
                raise e

        current_count = resp.get('meta').get('pagination').get('total')
    else:
        current_count = count
    # Determine new number of entries by comparing the DB record count to the
    # "total" field on the response meta
    if current_count == num_instance_in_db:
        return

    diff_count = current_count - num_instance_in_db
    logger.info('Fetch and sync %d new transactions', diff_count)

    orders = fetch_orders(order_type, diff_count, offset=offset, test=test)

    for order in orders:
        if order.get('reference'):
            order['transaction_id'] = order.get('external_transaction_id')
        order['transaction_type'] = order_type
        serializer = LoadTransactionSerializer(data=order)
        if not serializer.is_valid():
            logger.error('Error while serializing %s with ID %s. %s.',
                         order_type, order.get('id'),
                         serializer.error_messages)
            logger.error(serializer.errors)
            current_count -= 1
        else:
            serializer.create(serializer.validated_data)
        offset += 1

    # offset = Order.objects.filter(transaction_type=order_type).count()
    sync_order_db(order_type, current_count, offset, test)


def update_outlet_data(phone_number):
    try:
        resp = coinsph.fetch_outlet_data(phone_number)
    except Exception as e:
        logger.exception(
            "Something went wrong while trying to fetch %s outlet data",
            phone_number)
        raise e

    if resp.status_code != status.HTTP_200_OK:
        raise serializers.ValidationError(resp.json())

    resp = resp.json()
    try:
        payout_outlet = resp.get('payout-outlets')[0]
    except IndexError:
        raise serializers.ValidationError('Number is not supported')

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
