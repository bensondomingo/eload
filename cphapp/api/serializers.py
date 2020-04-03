from rest_framework import serializers

from cphapp.models import Transactions

class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transactions
        fields = '__all__'