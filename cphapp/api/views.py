import logging
from uuid import uuid4

from django.db.models import Q
from django.http import QueryDict

from rest_framework import serializers
from rest_framework import mixins, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters

from cphapp.models import LoadOutlet, LoadTransaction
from cphapp.api.serializers import (
    LoadOutletSerializer, LoadTransactionSerializer)
from cphapp.filters import TransactionsFilter
from cphapp.tasks import update_order_data
from cphapp.utility import update_outlet_data

from cph.coinsph import request_new_order

logger = logging.getLogger(__name__)


class TransactionAPIViewset(viewsets.GenericViewSet,
                            mixins.ListModelMixin,
                            mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin):

    serializer_class = LoadTransactionSerializer
    permission_classes = [IsAuthenticated]
    queryset = LoadTransaction.objects.all()
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TransactionsFilter

    def get_queryset(self):
        if self.request.user.is_staff:
            return super().get_queryset()

        sellorders = super().get_queryset().filter(
            transaction_type='sellorder')

        retailer_device_list = self.request.user.profile.devices.all()
        if not retailer_device_list.exists():
            return self.request.user.profile.load_transactions.all()

        return sellorders.filter(
            Q(retailer=self.request.user.profile) |
            Q(device__in=retailer_device_list))

    def list(self, request, *args, **kwargs):
        # sync_order_db('sellorder')
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        raw_data = request.data
        if isinstance(request.data, QueryDict):
            raw_data = raw_data.copy()
        # Add an id if none is provided on the request data
        raw_data.setdefault('id', uuid4().hex)

        # Validation
        s = LoadTransactionSerializer(data=raw_data)
        if not s.is_valid():
            raise serializers.ValidationError(detail=s.errors)

        # Format data
        data = {
            'amount': raw_data.get('amount'),
            'currency': 'PHP',
            'payment_outlet': raw_data.get('outlet_id'),
            'pay_with_wallet': 'PBTC',
            'phone_number_load': raw_data.get('phone_number'),
            'external_transaction_id': raw_data.get('id'),
            'reference': {
                "retailer": request.user.username,
                "retailer_email": request.user.email
            }
        }

        if raw_data.get('product_code', False):
            data['product_code'] = raw_data.get('product_code')

        resp = request_new_order(data)
        resp_data = resp.json()
        order_data = resp_data.get('order')

        if resp_data.get('success'):
            transaction_id = data.get('external_transaction_id')
            order_data.update({
                'transaction_id': transaction_id,
                'transaction_type': 'sellorder'})

            serializer = LoadTransactionSerializer(data=order_data)
            if not serializer.is_valid():
                """
                Can't think of a scenario that this would fail, unless the
                serialization mapping was changed.
                """
                logger.error(serializer.errors)
                # TODO: Cache data and errors to redis
                # TODO: send notification alert to admin
                raise serializers.ValidationError(serializer.error_messages)
            serializer.save()
            update_order_data.apply_async(kwargs={'id': transaction_id})
            return Response(data=resp_data, status=status.HTTP_201_CREATED)

        else:
            if resp_data.get('status') == status.HTTP_400_BAD_REQUEST \
                    and resp_data.get('errors') is not None:
                return Response(data=resp_data,
                                status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        phone_number = request.GET.get('phone_number')
        prefix = phone_number[:6]
        try:
            outlet = LoadOutlet.objects.get(
                phone_number_prefixes__contains=[prefix])
        except LoadOutlet.DoesNotExist:
            outlet = update_outlet_data(phone_number)

        s = LoadOutletSerializer(instance=outlet)
        return Response(s.data)
