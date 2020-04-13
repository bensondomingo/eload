import pytz
from django.utils import timezone

from cph import coinsph


def group_entries(entries):
    return_value = list()
    for index, entry in enumerate(entries):
        reason_code = entry['reference'].get('reason_code')
        if reason_code == 'sell_order':
            continue
        status = entry.get('status')
        if reason_code == 'buy_order':
            transaction_type = 'buy'
            sell_amount = 0
            reward_amount = 0
            posted_amount = entry.get('posted_amount')
            buy_amount = entry.get('amount')
        elif reason_code == 'reward':
            buy_amount = 0
            transaction_type = 'sell'
            try:
                sell_order = entries[index+1]
            except IndexError:
                entry['partial'] = True
                yield entry
                break
            if status != 'success':
                reward_amount = 0
                posted_amount = 0
            else:
                reward_amount = float(entry.get('amount'))
                sell_amount = float(sell_order.get('amount'))
                posted_amount = -1 * (sell_amount - reward_amount)

        yield {'id': entry.get('id'),
                'account': entry.get('account'),
                'transaction_type': transaction_type,
                'status': status,
                'reward_amount': reward_amount,
                'sell_amount': sell_amount,
                'posted_amount': posted_amount,
                'buy_amount': buy_amount,
                'running_balance': entry.get('running_balance'),
                'transaction_date': entry.get('created_at')}


def utc_to_local(utc_datetime, local_tz):
    local_dt = utc_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)
