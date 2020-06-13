import pytz
from datetime import datetime

from cph import coinsph


class OrderList(list):
    def __init__(self, *args):
        super().__init__(args)

    def __sub__(self, other):
        return self.__class__(*[item for item in self if item not in other])


def utc_to_local(utc_datetime, local_tz):
    local_dt = utc_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def find_sell_order_pair(sell_order, entries):

    created_at = datetime.fromisoformat(sell_order['created_at'][:-1])
    matched_by_ref_and_dt = [
        e for e in entries
        if (e['reference'].get('reason_code') == 'reward'
            or e['reference'].get('purpose') == 'refund')
        and (datetime.fromisoformat(e['created_at'][:-1]) -
             created_at).total_seconds() > 0]

    try:
        assert(matched_by_ref_and_dt)
    except AssertionError:
        result = find_sell_order_pair(sell_order, entries)
        return result
    else:
        if len(matched_by_ref_and_dt) > 1:
            rb = float(sell_order['running_balance'])
            matched_by_rebates = [
                e for e in matched_by_ref_and_dt
                if rb + float(e['amount']) == float(e['running_balance'])]
            try:
                match = matched_by_rebates.__iter__().__next__()
            except StopIteration:
                return None
        else:
            match = matched_by_ref_and_dt.__iter__().__next__()

        entries.remove(match)
        return match


def group_entries(entries):
    buy_orders = list(filter(
        lambda e: e['reference']['reason_code'] == 'buy_order', entries))

    possible_matches = [e for e in entries
                        if e['reference']['reason_code'] == 'reward'
                        or e['reference'].get('purpose') == 'refund']

    for e in [e for e in entries if e not in possible_matches]:
        if e in buy_orders:
            yield e
        else:
            pair = find_sell_order_pair(e, possible_matches)
            if not pair:
                e['unpaired'] = True
                yield e
                continue
            e.update({'pair': pair})
            yield e
        continue

    if possible_matches:
        yield possible_matches


def sync_transactions_db(model, serializer):
    buy_order_count = model.objects.filter(
        transaction_type='buy_order').count()
    sell_order_count = model.objects.filter(
        transaction_type='sell_order').count()

    response = coinsph.get_crypto_payments(per_page=1, page=1)
    actual_count = response['meta']['total_count']
    if actual_count == buy_order_count + 2 * sell_order_count:
        return

    # Get last transaction entry from database
    try:
        latest_entry = model.objects.latest('transaction_date')
        PER_PAGE = 10
    except model.DoesNotExist:
        latest_entry_id = None
        PER_PAGE = 100
    else:
        latest_entry_id = latest_entry.id

    page = 1
    terminate_loop = False
    unpaired_order = []
    while not terminate_loop:
        response = coinsph.get_crypto_payments(page=page, per_page=PER_PAGE)
        meta = response.get('meta')
        crypto_payments = response.get('crypto-payments')
        page = meta.get('next_page', None)

        entries = crypto_payments + unpaired_order
        unpaired_order = []
        for transaction in group_entries(entries):
            try:
                # Only non-paired have entry_type key
                transaction['unpaired']
            except KeyError:
                pass
            except TypeError:
                unpaired_order += transaction
                continue
            else:
                unpaired_order.append(transaction)
                continue

            if transaction.get('id') == latest_entry_id:
                terminate_loop = True
                break
            s = serializer(data=transaction)
            if not s.is_valid():
                # TODO: Add error handling if transaction has an
                # invalid data. Maybe put it in logs
                # print(s.errors)
                pass
            else:
                s.create(s.validated_data)

        if not page:
            terminate_loop = True


def fetch_orders(order_type, count, offset=0):
    sell_orders = []
    limit = count if count <= 100 else 100
    remaining = count - limit
    response = coinsph.fetch_orders(order_type, limit=limit, offset=offset)
    sell_orders += response.get('orders')
    if remaining == 0:
        return sell_orders
    else:
        sell_orders += fetch_orders('sellorder',
                                    remaining, offset=offset + limit)
    return sell_orders


def sync_order_db(order_type, model, serializer):
    num_instance_in_db = model.objects.count()
    response = coinsph.fetch_orders(order_type, limit=1)
    current_count = response.get('meta').get('pagination').get('total')
    if current_count == num_instance_in_db:
        return

    diff_count = current_count - num_instance_in_db
    orders = fetch_orders(order_type, diff_count)

    for order in orders:
        s = serializer(data=order)
        if not s.is_valid():
            # TODO: Add error handling if transaction has an
            # invalid data. Maybe put it in logs
            # print(s.errors)
            pass
        else:
            s.create(s.validated_data)


def load_order_data_map(data):
    return {
        'id': data.get('id'),
        'user_agent': data.get('user_agent'),
        'amount': data.get('amount'),
        'status': data.get('delivery_status'),
        'fee': data.get('currency_fees'),
        'order_date': datetime.fromtimestamp(
            int(data.get('created_time'))).isoformat(),
        'phone_number': data.get('phone_number_load'),
        'network': data.get('payment_outlet_name'),
    }


def buy_order_data_map(data):
    return {
        'id': data.get('id'),
        'user_agent': data.get('user_agent'),
        'amount': data.get('subtotal'),
        'fee': data.get('payment_method_fee'),
        'status': data.get('status'),
        'payment_method': data.get('payment_outlet_id'),
        'order_date': datetime.fromtimestamp(
            int(data.get('created_at'))).isoformat(),
    }


def transaction_data_map(data):
    transaction_type = data['reference']['reason_code']
    mapped_data = {
        'id': data.get('id'),
        'account': data.get('account'),
        'transaction_type': transaction_type,
        'amount': data.get('amount'),
        'posted_amount': data.get('posted_amount'),
        'transaction_date': data.get('created_at'),
        'order_id': data.get('reference')['order_id']
    }

    if transaction_type == 'buy_order':
        mapped_data.update({
            'status': data.get('status'),
            'running_balance': data.get('running_balance')
        })
    elif transaction_type == 'sell_order':
        pair = data.get('pair')
        mapped_data.update({
            'status': pair['reference'].get('purpose') or 'success',
            'reward_amount': pair.get('amount'),
            'running_balance': pair.get('running_balance'),
            'reward_id': pair.get('id')
        })

    return mapped_data
