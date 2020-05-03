from datetime import datetime
from dateutil.relativedelta import relativedelta
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework import mixins

from cphapp.models import Transactions
from cphapp.api.serializers import TransactionSerializer

from cph import coinsph
from cphapp import utils


class TransactionsListAPIView(generics.ListAPIView):

    serializer_class = TransactionSerializer
    queryset = Transactions.objects.all()

    def list(self, request, *args, **kwargs):
        utils.sync_transactions_db(
            model=Transactions, serializer=self.serializer_class)
        return super().list(request, *args, **kwargs)


class TransactionsRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):

    serializer_class = TransactionSerializer
    queryset = Transactions.objects.all()


class TransactionsInitDBAPIView(APIView):

    def get(self, requests, **kwargs):
        response = coinsph.get_crypto_payments(page=1, per_page=100)
        crypto_payments = response.get('crypto-payments')
        transactions = list(utils.group_entries(crypto_payments))
        serializer = TransactionSerializer(data=transactions, many=True)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(data={'error': 'Something wen\'t wrong'},
                            status=status.HTTP_404_NOT_FOUND)

        transactions = Transactions.objects.all()
        serializer = TransactionSerializer(instance=transactions, many=True)

        return Response(data=serializer.data, status=status.HTTP_200_OK)
