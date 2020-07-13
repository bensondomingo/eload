from rest_framework import generics

from django_filters import rest_framework as filters
from rest_framework.permissions import IsAuthenticated

from cphapp.models import (Order, Transaction)
from cphapp.api.serializers import (OrderSerializer, TransactionSerializer)

from cphapp.filters import TransactionsFilter
from cphapp import utils


class TransactionsListAPIView(generics.ListAPIView):

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    queryset = Transaction.objects.all()
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TransactionsFilter

    def get_queryset(self):
        if self.request.user.is_staff:
            return super().get_queryset()

        device_hash = self.request.user.profile.user_agent.device_hash
        sell_orders = super().get_queryset().filter(
            transaction_type='sell_order')
        return sell_orders.filter(order__user_agent__device_hash=device_hash)

    def list(self, request, *args, **kwargs):
        # Update database
        # if not request.query_params.get('offset'):
        #     utils.sync_transactions_db(Transaction, TransactionSerializer)
        #     utils.sync_order_db('sellorder', Order, OrderSerializer)
        #     utils.sync_order_db('buyorder', Order, OrderSerializer)
        return super().list(request, *args, **kwargs)


class OrderListAPIView(generics.ListAPIView):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get_queryset(self):
        order_type = self.request.query_params.get('order_type', 'all')
        if order_type == 'all':
            return super().get_queryset()
        else:
            return self.queryset.filter(order_type=order_type)

    def list(self, request, *args, **kwargs):
        utils.sync_order_db('sellorder', Order, OrderSerializer)
        utils.sync_order_db('buyorder', Order, OrderSerializer)
        return super().list(request, *args, **kwargs)
