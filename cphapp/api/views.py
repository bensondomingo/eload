from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters

from cphapp.models import LoadOutlet, LoadTransaction
from cphapp.api.serializers import (
    LoadOutletSerializer, LoadTransactionSerializer)
from cphapp.filters import TransactionsFilter
from cphapp.utility import update_outlet_data


class TransactionAPIViewset(viewsets.GenericViewSet,
                            mixins.CreateModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.ListModelMixin):

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
        try:
            device_hash = self.request.user.profile.user_agent.device_hash
        except AttributeError:
            return sellorders.filter(retailer=self.request.user)
        else:
            return sellorders.filter(
                Q(retailer=self.request.user) |
                Q(user_agent__device_hash=device_hash))


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

    def post(self, request, *args, **kwargs):
        pass


# class LoadTransactionAPIViewset(viewsets.GenericViewSet,
#                                 mixins.ListModelMixin,
#                                 mixins.CreateModelMixin,
#                                 mixins.RetrieveModelMixin,
#                                 mixins.UpdateModelMixin,
#                                 mixins.DestroyModelMixin):

#     queryset = LoadTransaction.objects.all()
#     serializer_class = LoadTransactionSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         if self.request.user.is_staff:
#             return super().get_queryset()
#         return super().get_queryset().filter(retailer=self.request.user)
