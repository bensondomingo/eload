import django_filters
from django_filters import FilterSet
from cphapp.models import Transactions


class TransactionsFilter(FilterSet):

    class Meta:
        model = Transactions
        fields = {
            'buy_amount': ['exact', 'lt', 'lte', 'gt', 'gte'],
            'sell_amount': ['exact', 'lt', 'lte', 'gt', 'gte'],
            'transaction_type': ['exact'],
            'transaction_date': ['lte', 'lt', 'gte', 'gt', 'year', 'month', 'day']
        }
