from datetime import datetime, timedelta
from django_filters import rest_framework as filters
from cphapp.models import Transaction


date_range_map = {
    'today': {
        'transaction_date__day': datetime.now().day,
        'transaction_date__month': datetime.now().month,
        'transaction_date__year': datetime.now().year
    },
    'yesterday': {
        'transaction_date__day': datetime.now().day - 1,
        'transaction_date__month': datetime.now().month,
        'transaction_date__year': datetime.now().year
    }
}


class TransactionsFilter(filters.FilterSet):
    td_gte = filters.DateTimeFilter(
        field_name='transaction_date', lookup_expr='gte')
    td_lte = filters.DateTimeFilter(
        field_name='transaction_date', method='filter_date_lte')
    ctd_gte = filters.IsoDateTimeFilter(
        field_name='transaction_date', lookup_expr='gte')
    ctd_lte = filters.IsoDateTimeFilter(
        field_name='transaction_date', lookup_expr='lte')

    def filter_date_lte(self, queryset, name, value):
        # Add 1 day on the filter date, consider 12:00 AM
        dt = value + timedelta(hours=23, minutes=59)
        return queryset.filter(transaction_date__lte=dt)

    class Meta:
        model = Transaction
        fields = {
            'transaction_date': ['year', 'month', 'day'],
        }
