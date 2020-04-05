from datetime import datetime
from dateutil.relativedelta import relativedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from cphapp.models import Transactions
from cphapp.api.serializers import TransactionSerializer

from cph import coinsph
from cphapp import utils


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
            response = coinsph.get_crypto_payments(
                page=1, per_page=100, all=True)
            crypto_payments = response.get('crypto-payments')
            for transaction in utils.group_entries(crypto_payments):
                serializer = TransactionSerializer(data=transaction)
                if not serializer.is_valid():
                    return Response(data=serializer.error_messages,
                                    status=status.HTTP_400_BAD_REQUEST)
                serializer.create(serializer.validated_data)

        else:
            page = 1
            terminate_loop = False
            transactions = list()
            while True:
                response = coinsph.get_crypto_payments(page=page, per_page=10)
                page = response['meta'].get('next_page')
                crypto_payments = response.get('crypto-payments')

                if len([c for c in crypto_payments if c['reference'].get(
                        'reason_code') == 'buy_order']) % 2:
                    _r = coinsph.get_crypto_payments(page=page, per_page=10)
                    _c = _r.get('crypto-payments')
                    crypto_payments.append(_c[0])

                for transaction in utils.group_entries(crypto_payments):
                    if transaction.get('id') == latest_entry.id:
                        terminate_loop = True
                        break
                    serializer = TransactionSerializer(data=transaction)
                    if not serializer.is_valid():
                        return Response(data=serializer.error_messages,
                                        status=status.HTTP_400_BAD_REQUEST)
                    serializer.create(serializer.validated_data)

                if not terminate_loop:
                    continue
                break

        finally:
            transaction_objects = Transactions.objects.all()
            serializer = TransactionSerializer(
                instance=transaction_objects, many=True)
            return Response(data=serializer.data, status=status.HTTP_200_OK)
