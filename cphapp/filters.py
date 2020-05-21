import django_filters
from django_filters import FilterSet
from cphapp.models import Transaction


class TransactionsFilter(FilterSet):

    class Meta:
        model = Transaction
        fields = {
            'amount': ['exact', 'lt', 'lte', 'gt', 'gte'],
            'transaction_type': ['exact'],
            'transaction_date': ['lte', 'lt', 'gte', 'gt', 'year', 'month', 'day'],
            'order_id': ['exact'],
            'reward_id': ['exact']
        }
