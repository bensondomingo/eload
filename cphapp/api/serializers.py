from datetime import datetime

from rest_framework import serializers
from rest_framework.fields import empty

from cphapp.models import Transaction
from cphapp.models import UserAgent


class UserAgentSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserAgent
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    user_agent = UserAgentSerializer()

    class Meta:
        model = Transaction
        fields = '__all__'

    def __init__(self, instance=None, data=empty, **kwargs):
        if data != empty and not kwargs.get('partial'):
            data = TransactionDetailSerializer.order_to_transactions_map(data)
        super().__init__(instance=instance, data=data, **kwargs)

    @staticmethod
    def order_to_transactions_map(data):
        parsed = {
            'id': data.get('id'),
            'confirmation_code': data.get('confirmation_code'),
            'account': data.get('user_id'),
            'user_agent': data.get('user_agent'),
            'transaction_type': data.get('transaction_type'),
            'status': data.get('delivery_status') or data.get('status'),
            'amount': data.get('amount') or data.get('subtotal'),
            'fee': data.get('currency_fees') or data.get('coins_fee'),
            'transaction_date': datetime.fromtimestamp(
                int(data.get('created_time'))).isoformat(),
        }
        if data.get('transaction_type') == 'sellorder':
            parsed.update({
                'phone_number': data.get('phone_number_load'),
                'network': data.get('payment_outlet_name')
            })
        else:
            parsed['payment_method'] = data.get('payment_outlet_id')

        return parsed

    def create(self, validated_data):
        # Use user_agent to bind this transaction to a retailer
        ua_dict = self.initial_data.get('user_agent')
        ua_query = 'device_hash' if ua_dict.get('device_hash') else 'browser'
        query_dict = {ua_query: ua_dict.get(ua_query)}

        try:
            user_agent = UserAgent.objects.get(**query_dict)
        except UserAgent.DoesNotExist:
            serializer = UserAgentSerializer(
                data=self.initial_data.get('user_agent'))
            if not serializer.is_valid():
                pass
            user_agent = serializer.create(serializer.validated_data)
        finally:
            validated_data['user_agent'] = user_agent

        status = validated_data.get('status')
        if status == 'expired' or status == 'canceled':
            return super().create(validated_data)

        return super().create(validated_data)


class TransactionDetailSerializer(TransactionSerializer):
    phone_number = serializers.CharField(source='loadorder.phone_number')
    network = serializers.CharField(source='loadorder.network')

    class Meta(TransactionSerializer.Meta):
        fields = '__all__'

    def __init__(self, instance, *args, **kwargs):
        super(TransactionDetailSerializer, self).__init__(
            instance, *args, **kwargs)
        if instance.transaction_type == 'buy_order':
            self.fields.pop('phone_number')
            self.fields.pop('network')
