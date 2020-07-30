from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters

from cphapp.models import Transaction
from cphapp.api.serializers import TransactionSerializer
from cphapp.filters import TransactionsFilter


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
        sellorders = super().get_queryset().filter(
            transaction_type='sellorder')
        return sellorders.filter(user_agent__device_hash=device_hash)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
