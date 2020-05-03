import pytz
from datetime import datetime
from django.utils import timezone

from cph import coinsph


def utc_to_local(utc_datetime, local_tz):
    local_dt = utc_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def group_entries(entries):
    for index, entry in enumerate(entries):
        reason_code = entry['reference'].get('reason_code')
        status = entry.get('status')
        if reason_code == 'sell_order':
            continue
        elif reason_code == 'buy_order':
            transaction_type = 'buy'
            sell_amount = 0
            reward_amount = 0
            posted_amount = entry.get('posted_amount')
            buy_amount = entry.get('amount')
        elif reason_code == 'reward':
            try:
                sell_order = entries[index+1]
            except IndexError:
                entry['partial'] = True
                yield entry
                break
            buy_amount = 0
            transaction_type = 'sell'
            reward_amount = float(entry.get('amount'))
            sell_amount = float(sell_order.get('amount'))
            posted_amount = -1 * (sell_amount - reward_amount)
        else:
            pass

        data = {'id': entry.get('id'),
                'account': entry.get('account'),
                'transaction_type': transaction_type,
                'status': status,
                'reward_amount': reward_amount,
                'sell_amount': sell_amount,
                'posted_amount': posted_amount,
                'buy_amount': buy_amount,
                'running_balance': entry.get('running_balance'),
                'transaction_date': entry.get('created_at')}

        if data['transaction_type'] == 'sell':
            # Need this data in sell validation
            data['sell_transaction_date'] = sell_order.get('created_at')
            data['balance_before_reward'] = float(
                sell_order.get('running_balance'))

        yield data


def sync_transactions_db(model, serializer):
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
    unconsumed_data = None
    while not terminate_loop:
        if not unconsumed_data:
            response = coinsph.get_crypto_payments(
                page=page, per_page=PER_PAGE)
        else:
            response = unconsumed_data
            unconsumed_data = None
        meta = response.get('meta')
        crypto_payments = response.get('crypto-payments')
        page = meta.get('next_page', None)

        for transaction in group_entries(crypto_payments):
            try:
                partial = transaction['partial']
            except KeyError:
                pass

            else:
                # complete partial data
                unconsumed_data = coinsph.get_crypto_payments(
                    page=page, per_page=PER_PAGE)
                _cp = unconsumed_data['crypto-payments']
                _t = list(group_entries([transaction, _cp.pop(0)]))
                transaction = _t[0]

            finally:
                if transaction.get('id') == latest_entry_id:
                    terminate_loop = True
                    break
                s = serializer(data=transaction)
                if not s.is_valid():
                    # TODO: Add error handling if transaction has an
                    # invalid data. Maybe put it in logs
                    pass
                else:
                    s.create(s.validated_data)

        if not page:
            terminate_loop = True
