from rest_framework import serializers
from rest_framework.fields import empty

from cphapp.models import Transaction
from cphapp.models import UserAgent
from cphapp.models import LoadOrder
from cphapp.models import BuyOrder
from cphapp.utils import (sync_transactions_db, transaction_data_map,
                          load_order_data_map, buy_order_data_map)


class UserAgentSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserAgent
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    # phone_number = serializers.SerializerMethodField()
    user_agent = UserAgentSerializer(source='order.user_agent')

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
        fields = '__all__'

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

        if validated_data.get('status') == 'canceled':
            validated_data['transaction'] = None
            return super().create(validated_data)

        try:
            transaction = Transaction.objects.get(
                order_id=validated_data['id'])
        except Transaction.DoesNotExist:
            sync_transactions_db(
                model=Transaction, serializer=TransactionSerializer)
            transaction = Transaction.objects.get(
                order_id=validated_data['id'])
        finally:
            validated_data['transaction'] = transaction

        return super().create(validated_data)


class LoadOrderSerializer(OrderSerializer):

    class Meta(OrderSerializer.Meta):
        model = LoadOrder

    def __init__(self, instance=None, data=empty, **kwargs):
        if data != empty:
            data = load_order_data_map(data)
        super().__init__(instance=instance, data=data, **kwargs)


class LoadOrderDetailSerializer(LoadOrderSerializer):
    user_agent = UserAgentSerializer(read_only=True)
    transaction = TransactionSerializer(read_only=True)

    class Meta(LoadOrderSerializer.Meta):
        fields = '__all__'


class BuyOrderSerializer(OrderSerializer):

    class Meta(OrderSerializer.Meta):
        model = BuyOrder

    def __init__(self, instance=None, data=empty, **kwargs):
        if data != empty:
            data = buy_order_data_map(data)
        super().__init__(instance=instance, data=data, **kwargs)
