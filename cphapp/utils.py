import pytz
from datetime import datetime
from django.utils import timezone

from cph import coinsph


def utc_to_local(utc_datetime, local_tz):
    local_dt = utc_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def find_sell_order_pair(sell_order, entries):

    created_at = datetime.fromisoformat(sell_order['created_at'][:-1])
    matched_by_ref_and_dt = [
        e for e in entries
        if (e['reference'].get('reason_code') == 'reward' or e['reference'].get('purpose') == 'refund')
        and (datetime.fromisoformat(e['created_at'][:-1]) - created_at).total_seconds() > 0]

    try:
        assert(matched_by_ref_and_dt)
    except AssertionError:
        result = find_sell_order_pair(sell_order, entries)
        return result
    else:
        if len(matched_by_ref_and_dt) > 1:
            order_running_balance = float(sell_order['running_balance'])
            matched_by_rebates = [
                e for e in matched_by_ref_and_dt
                if order_running_balance + float(e['amount']) == float(e['running_balance'])]
            try:
                match = matched_by_rebates.__iter__().__next__()
            except StopIteration:
                return None
        else:
            match = matched_by_ref_and_dt.__iter__().__next__()

        entries.remove(match)
        return match


def group_entries(entries):
    sell_orders = filter(lambda e: e['reference']['reason_code'] == 'sell_order'
                         and not e['reference'].get('purpose'), entries)
    buy_orders = filter(lambda e: e['reference']
                        ['reason_code'] == 'buy_order', entries)

    possible_matches = [e for e in entries
                        if e['reference']['reason_code'] == 'reward'
                        or e['reference'].get('purpose') == 'refund']

    for buy_order in buy_orders:
        yield {
            'id': buy_order.get('id'),
            'account': buy_order.get('account'),
            'transaction_type': 'buy_order',
            'status': buy_order.get('status'),
            'amount': buy_order.get('amount'),
            'posted_amount': buy_order.get('posted_amount'),
            'running_balance': buy_order.get('running_balance'),
            'order_id': buy_order['reference'].get('order_id'),
            'transaction_date': buy_order.get('created_at')
        }
        continue

    for sell_order in sell_orders:
        pair = find_sell_order_pair(sell_order, possible_matches)
        if not pair:
            yield sell_order
            continue
        yield {
            'id': sell_order.get('id'),
            'account': sell_order.get('account'),
            'transaction_type': 'sell_order',
            'status': 'refunded' if pair['reference'].get('purpose') else 'success',
            'amount': sell_order.get('amount'),
            'reward_amount': pair.get('amount'),
            'posted_amount': sell_order.get('posted_amount'),
            'running_balance': pair.get('running_balance'),
            'order_id': sell_order['reference'].get('order_id'),
            'reward_id': pair.get('id'),
            'transaction_date': sell_order.get('created_at')
        }
        continue

    if possible_matches:
        yield possible_matches


def sync_transactions_db(model, serializer):
    buy_order_count = model.objects.filter(
        transaction_type='buy_order').count()
    sell_order_count = model.objects.filter(
        transaction_type='sell_order').count()

    response = coinsph.get_crypto_payments(per_page=1, page=1)
    if response['meta']['total_count'] == buy_order_count + 2 * sell_order_count:
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
                transaction['entry_type']
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
                print(s.errors)
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
        data = {
            'id': order.get('id'),
            'user_agent': order.get('user_agent'),
        }

        if order_type == 'sellorder':
            data.update({
                'amount': order.get('amount'),
                'status': order.get('delivery_status'),
                'fee': order.get('currency_fees'),
                'order_date': datetime.fromtimestamp(
                    int(order.get('created_time'))).isoformat(),
                'phone_number': order.get('phone_number_load'),
                'network': order.get('payment_outlet_name'),
            })
        else:
            data.update({
                'amount': order.get('subtotal'),
                'fee': order.get('payment_method_fee'),
                'status': order.get('status'),
                'payment_method': order.get('payment_outlet_id'),
                'order_date': datetime.fromtimestamp(
                    int(order.get('created_at'))).isoformat(),
            })

        s = serializer(data=data)
        if not s.is_valid():
            # TODO: Add error handling if transaction has an
            # invalid data. Maybe put it in logs
            pass
        else:
            s.create(s.validated_data)


def sync_sell_order_db(model, serializer):
    db_count = model.objects.count()
    response = coinsph.fetch_orders('sellorder', limit=1)
    current_count = response.get('meta').get('pagination').get('total')
    if current_count == db_count:
        return
    diff_count = current_count - db_count
    sell_orders = fetch_orders('sellorder', diff_count)

    for sell in sell_orders:
        # order_date = datetime.fromtimestamp(int(sell.get('created_time')))
        sell_data = {
            'id': sell.get('id'),
            'amount': sell.get('amount'),
            'status': sell.get('delivery_status'),
            'fee': sell.get('currency_fees'),
            'order_date': datetime.fromtimestamp(
                int(sell.get('created_time'))).isoformat(),
            'phone_number': sell.get('phone_number_load'),
            'network': sell.get('payment_outlet_name'),
            'payment_id': sell.get('payments')[0].get('transaction_ref'),
            'user_agent': sell.get('user_agent')
        }
        s = serializer(data=sell_data)
        if not s.is_valid():
            # TODO: Add error handling if transaction has an
            # invalid data. Maybe put it in logs
            pass
        else:
            s.create(s.validated_data)


def sync_buy_order_db(model, serializer):
    pass
