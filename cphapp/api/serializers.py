import pytz
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import serializers
from rest_framework.fields import empty

from uuid import uuid4

from cphapp.models import (LoadOutlet, LoadTransaction, Device)
from cphapp.exceptions import LoadAmountError

from profiles.models import Profile as Retailer


class LoadOutletSerializer(serializers.ModelSerializer):
    phone_number_prefixes = serializers.ListField(read_only=True)

    class Meta:
        model = LoadOutlet
        fields = '__all__'


class UserAgentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Device
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(max_length=13, min_length=13)
    sold_this_month = serializers.SerializerMethodField()
    reward_amount = serializers.SerializerMethodField()
    network = serializers.SerializerMethodField()

    class Meta:
        model = LoadTransaction
        fields = '__all__'

    @staticmethod
    def get_user_agent(ua_dict):
        ua_query = 'device_hash' if ua_dict.get('device_hash') else 'browser'
        query_dict = {ua_query: ua_dict.get(ua_query)}

        try:
            user_agent = Device.objects.get(**query_dict)
        except Device.DoesNotExist:
            serializer = UserAgentSerializer(data=ua_dict)
            if not serializer.is_valid():
                # Need to call is_valid() before deserialization
                pass
            user_agent = serializer.create(serializer.validated_data)
        return user_agent

    def get_sold_this_month(self, instance):
        return instance.sold_this_month

    def get_reward_amount(self, instance):
        return instance.reward_amount

    def get_network(self, instance):
        return instance.network


class LoadTransactionSerializer(serializers.ModelSerializer):
    sold_this_month = serializers.SerializerMethodField()
    network = serializers.SerializerMethodField()
    device_hash = serializers.CharField(
        source='device.device_hash', read_only=True)

    class Meta:
        model = LoadTransaction
        fields = '__all__'

    def __init__(self, instance=None, data=empty, **kwargs):
        '''
        POST request data contains value for required fields only. Optional
        fields are filled later by a worker.
        '''

        if data is not empty:
            if data.get('confirmation_code', False):
                # Having confirmation_code means the data came from a response
                data = LoadTransactionSerializer.order_to_transactions_map(
                    data)

        super().__init__(instance=instance, data=data, **kwargs)

    @staticmethod
    def get_user_agent(ua_dict):
        # Update will be performed by worker that polls the sellorder
        ua_query = 'device_hash' if ua_dict.get(
            'device_hash') else 'user_agent'
        query_dict = {ua_query: ua_dict.get(ua_query)}

        try:
            user_agent = Device.objects.get(**query_dict)
        except Device.DoesNotExist:
            serializer = UserAgentSerializer(data=ua_dict)
            if not serializer.is_valid():
                # Need to call is_valid() before deserialization
                pass
            user_agent = serializer.create(serializer.validated_data)
        return user_agent

    @staticmethod
    def get_retailer(reference_field):
        if not reference_field:
            return None

        retailer_username = reference_field.get('retailer')
        try:
            retailer = Retailer.objects.get(user__username=retailer_username)
        except Retailer.DoesNotExist:
            return None
        else:
            return retailer.id

    @staticmethod
    def order_to_transactions_map(data):
        parsed = {
            'id': data.get('transaction_id', uuid4().hex),
            'order_id': data.get('id'),
            'outlet_id': data.get('payment_outlet_id'),
            'confirmation_code': data.get('confirmation_code'),
            'account': data.get('user_id'),
            # 'user_agent': data.get('user_agent'),
            'transaction_type': data.get('transaction_type'),
            'status': data.get('delivery_status') or data.get('status'),
            'amount': data.get('amount') or data.get('subtotal'),
            'product_code': data.get('product_code', 'regular'),
            'transaction_date': datetime.fromtimestamp(
                int(data.get('created_time')),
                pytz.timezone(settings.TIME_ZONE)).isoformat(),
            'running_balance': data.get('running_balance'),
            'posted_amount': data.get('posted_amount')
        }
        if data.get('transaction_type') == 'sellorder':
            parsed.update({
                'phone_number': data.get('phone_number_load'),
                'retailer': LoadTransactionSerializer.get_retailer(
                    data.get('reference'))
                # 'retailer': data.get('retailer'),
            })
        else:
            parsed['payment_method'] = data.get('payment_outlet_id')

        parsed['device'] = LoadTransactionSerializer.get_user_agent(
            data.get('user_agent')).id

        return parsed

    def get_sold_this_month(self, instance):
        return instance.sold_this_month

    def get_reward_amount(self, instance):
        return instance.reward_amount

    def get_network(self, instance):
        return instance.network

    def validate_phone_number(self, value):
        if len(value) != 13:
            raise serializers.ValidationError(
                'Phone number should be 13 characters')
        return value

    def validate(self, attrs):
        """ Validate Load amount based on outlet's valid amount range """

        if 'running_balance' in attrs and 'posted_amount' in attrs:
            # Skip amount validation during crypto-payment update
            return super().validate(attrs)

        if 'confirmation_code' not in attrs:
            # Perform this validation only during retailer initiated buy
            amount = attrs.get('amount')
            outlet = get_object_or_404(
                LoadOutlet, id=attrs.get('outlet_id'))
            # outlet = LoadOutlet.objects.get(id=attrs.get('outlet_id'))
            limits = next(filter(lambda o: o.get('currency') == 'PHP',
                                 outlet.amount_limits))
            mn = limits.get('minimum')
            mx = limits.get('maximum')
            try:
                assert(mn <= amount and amount <= mx)
            except AssertionError:
                err = LoadAmountError(amount, mn, mx)
                raise serializers.ValidationError(detail=err)
        return super().validate(attrs)
