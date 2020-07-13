from rest_framework import serializers
from rest_framework.fields import empty

from cphapp.models import Transaction
from cphapp.models import UserAgent
from cphapp.models import Order
from cphapp.utils import (transaction_data_map, order_data_map)


class UserAgentSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserAgent
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    user_agent = UserAgentSerializer(source='order.user_agent', read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'

    def __init__(self, instance=None, data=empty, **kwargs):
        if data != empty:
            data = transaction_data_map(data)
        super().__init__(instance=instance, data=data, **kwargs)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get('transaction_type') == 'sell_order':
            ret['phone_number'] = instance.order.phone_number
            ret['network'] = instance.order.network
        elif ret.get('transaction_type') == 'buy_order':
            ret['payment_method'] = instance.order.payment_method
        return ret


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


class OrderSerializer(serializers.ModelSerializer):
    user_agent = UserAgentSerializer(write_only=True)

    class Meta:
        model = Order
        fields = '__all__'

    def __init__(self, instance=None, data=empty, **kwargs):
        if data != empty:
            data = order_data_map(data)
        super().__init__(instance=instance, data=data, **kwargs)

    def create(self, validated_data):
        ua_dict = validated_data.get('user_agent')
        ua_query = 'device_hash' if ua_dict.get('device_hash') else 'browser'
        query_dict = {ua_query: ua_dict.get(ua_query)}

        try:
            user_agent = UserAgent.objects.get(**query_dict)
        except UserAgent.DoesNotExist:
            serializer = UserAgentSerializer(
                data=validated_data.get('user_agent'))
            if not serializer.is_valid():
                pass
            user_agent = serializer.create(serializer.validated_data)
        finally:
            validated_data['user_agent'] = user_agent

        status = validated_data.get('status')
        if status == 'expired' or status == 'canceled':
            validated_data['transaction'] = None
            return super().create(validated_data)

        validated_data['transaction'] = Transaction.objects.get(
            order_id=validated_data['id'])

        return super().create(validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret_value = {k: v for k, v in ret.items() if v is not None}
        return ret_value
