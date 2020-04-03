from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from cphapp.models import Transactions

from cph import coinsph

class TransactionsAPIView(APIView):

    def get(self, requests, **kwargs):
        transactions = coinsph.get_crypto_payments(per_page=100)
        return Response(data=transactions, status=status.HTTP_200_OK)