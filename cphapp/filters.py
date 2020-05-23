from django_filters import FilterSet
from cphapp.models import Transaction


class TransactionsFilter(FilterSet):

    class Meta:
        model = Transaction
        fields = {
            'order_id': ['exact'],
            'reward_id': ['exact'],
            'transaction_type': ['exact'],
            'amount': ['exact', 'lt', 'lte', 'gt', 'gte'],
            'transaction_date': ['lte', 'lt', 'gte', 'gt',
                                 'year', 'month', 'day'],
        }
