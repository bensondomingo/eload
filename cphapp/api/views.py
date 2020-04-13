from datetime import datetime
from dateutil.relativedelta import relativedelta
import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from cphapp.models import Transactions
from cphapp.api.serializers import TransactionSerializer

from cph import coinsph
from cphapp import utils

PER_PAGE = 10


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


class TransactionsAPIView(APIView):

    def get(self, requests, **kwargs):
        # Get last transaction entry from database
        try:
            latest_entry = Transactions.objects.latest('transaction_date')
        except Transactions.DoesNotExist:
            latest_entry_id = None
        else:
            latest_entry_id = latest_entry.id

        page = 1
        terminate_loop = False
        unconsumed_data = None
        while not terminate_loop:
            if not unconsumed_data:
                response = coinsph.get_crypto_payments(
                    page=page, per_page=PER_PAGE)
            else:
                response = unconsumed_data
                unconsumed_data = None
            meta = response.get('meta')
            crypto_payments = response.get('crypto-payments')
            page = meta.get('next_page', None)

            for transaction in utils.group_entries(crypto_payments):
                try:
                    partial = transaction['partial']
                except KeyError:
                    pass

                else:
                    # complete partial data
                    unconsumed_data = coinsph.get_crypto_payments(
                        page=page, per_page=PER_PAGE)
                    _cp = unconsumed_data['crypto-payments']
                    _t = list(utils.group_entries([transaction, _cp.pop(0)]))
                    transaction = _t[0]

                finally:
                    if transaction.get('id') == latest_entry_id:
                        terminate_loop = True
                        break
                    serializer = TransactionSerializer(data=transaction)
                    if not serializer.is_valid():
                        # TODO: Add error handling if transaction has an
                        # invalid data
                        pass
                    else:
                        serializer.create(serializer.validated_data)

            if not page:
                terminate_loop = True

        transactions_objects = Transactions.objects.all()
        serializer = TransactionSerializer(
            instance=transactions_objects, many=True)

        return Response(data=serializer.data, status=status.HTTP_200_OK)
