from rest_framework import generics

from django_filters import rest_framework as filters

from cphapp.models import (BuyOrder, LoadOrder, Transaction)
from cphapp.api.serializers import (
    BuyOrderSerializer, LoadOrderSerializer, LoadOrderDetailSerializer,
    TransactionSerializer, TransactionDetailSerializer)

from cphapp.filters import TransactionsFilter
from cphapp import utils


class TransactionsListAPIView(generics.ListAPIView):

    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TransactionsFilter

    def list(self, request, *args, **kwargs):
        # if not request.query_params.get('offset'):
        #     utils.sync_order_db('sellorder', model=LoadOrder,
        #                         serializer=LoadOrderSerializer)
        #     utils.sync_order_db('buyorder', model=BuyOrder,
        #                         serializer=BuyOrderSerializer)
        return super().list(request, *args, **kwargs)


class TransactionsRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):

    serializer_class = TransactionDetailSerializer
    queryset = Transaction.objects.all()


class SellLoadOrderListAPIView(generics.ListAPIView):

    serializer_class = LoadOrderSerializer
    queryset = LoadOrder.objects.all()

    def list(self, request, *args, **kwargs):
        if request.query_params.get('update'):
            utils.sync_order_db('sellorder', model=LoadOrder,
                                serializer=LoadOrderSerializer)
        return super().list(request, *args, **kwargs)


class SellLoadOrderRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):

    serializer_class = LoadOrderDetailSerializer
    queryset = LoadOrder.objects.all()


class BuyOrderListAPIView(generics.ListAPIView):

    serializer_class = BuyOrderSerializer
    queryset = BuyOrder.objects.all()

    def list(self, request, *args, **kwargs):
        if request.query_params.get('update'):
            utils.sync_order_db('buyorder', model=BuyOrder,
                                serializer=BuyOrderSerializer)
        return super().list(request, *args, **kwargs)


class BuyOrderRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):

    serializer_class = BuyOrderSerializer
    queryset = BuyOrder.objects.all()
