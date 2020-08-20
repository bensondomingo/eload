from datetime import datetime
from django.http import QueryDict

from rest_framework import serializers
from rest_framework.fields import empty

from cphapp.models import (LoadOutlet, LoadTransaction, UserAgent)
from cphapp.exceptions import LoadAmountError


class LoadOutletSerializer(serializers.ModelSerializer):
    phone_number_prefixes = serializers.ListField(read_only=True)

    class Meta:
        model = LoadOutlet
        fields = '__all__'


class UserAgentSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserAgent
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
            user_agent = UserAgent.objects.get(**query_dict)
        except UserAgent.DoesNotExist:
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
    phone_number = serializers.CharField(max_length=13, min_length=13)
    sold_this_month = serializers.SerializerMethodField()
    reward_amount = serializers.SerializerMethodField()
    network = serializers.SerializerMethodField()

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
            else:
                if not kwargs.get('partial', False):
                    # create triggered by a POST request from user
                    if isinstance(data, QueryDict):
                        data = data.copy()
                    data.update(
                        {'retailer': kwargs['context']['request'].user.id})

        super().__init__(instance=instance, data=data, **kwargs)

    @staticmethod
    def order_to_transactions_map(data):
        parsed = {
            'order_id': data.get('id'),
            'confirmation_code': data.get('confirmation_code'),
            'account': data.get('user_id'),
            # 'transaction_type': data.get('transaction_type'),
            'status': data.get('delivery_status'),
            # 'amount': data.get('amount') or data.get('subtotal'),
            # 'fee': data.get('currency_fees') or data.get('coins_fee'),
            'transaction_date': datetime.fromtimestamp(
                int(data.get('created_time'))).isoformat()
        }
        ua = LoadTransactionSerializer.get_user_agent(
            data.get('user_agent'))
        parsed.update({'user_agent': ua.id})
        return parsed

    @staticmethod
    def get_user_agent(ua_dict):
        # Update will be performed by worker that polls the sellorder
        ua_query = 'device_hash' if ua_dict.get('device_hash') else 'browser'
        query_dict = {ua_query: ua_dict.get(ua_query)}

        try:
            user_agent = UserAgent.objects.get(**query_dict)
        except UserAgent.DoesNotExist:
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

    def validate(self, attrs):
        if 'amount' in attrs.keys():
            amount = attrs.get('amount')
            outlet = LoadOutlet.objects.get(id=attrs.get('outlet_id'))
            limits = next(filter(lambda o: o.get('currency') == 'PHP',
                                 outlet.amount_limits))
            try:
                mn = limits.get('minimum')
                mx = limits.get('maximum')
                assert(mn <= amount and amount <= mx)
            except AssertionError:
                err = LoadAmountError(amount, mn, mx)
                raise serializers.ValidationError(detail=err)
        return super().validate(attrs)


# class RetailerTransactionSerializer(TransactionSerializer):

#     def __init__(self, instance=None, data=empty, **kwargs):
#         super().__init__(instance=instance, data=data, **kwargs)

        # class _TransactionSerializer(serializers.ModelSerializer):
        #     id = serializers.CharField(source='id.hex')  # UUID without hyphens
        #     user_agent = UserAgentSerializer()

        #     class Meta:
        #         model = LoadTransaction
        #         fields = '__all__'

        #     def __init__(self, instance=None, data=empty, **kwargs):

        #         if data != empty \
        #                 and data.get('transaction_type') is not None \
        #                 or kwargs.get('update'):
        #             """
        #             transaction_type field is not provided using POST and the default
        #             value based on model is sellorder. transaction_type is only
        #             provided during PUT or calling the sync_order_db from utils module.
        #             """
        #             data = TransactionSerializer.order_to_transactions_map(data)

        #         super().__init__(instance=instance, data=data, **kwargs)

        #     @staticmethod
        #     def order_to_transactions_map(data):
        #         parsed = {
        #             'order_id': data.get('id'),
        #             'confirmation_code': data.get('confirmation_code'),
        #             'account': data.get('user_id'),
        #             'user_agent': data.get('user_agent'),
        #             'transaction_type': data.get('transaction_type'),
        #             'status': data.get('delivery_status') or data.get('status'),
        #             'amount': data.get('amount') or data.get('subtotal'),
        #             'fee': data.get('currency_fees') or data.get('coins_fee'),
        #             'transaction_date': datetime.fromtimestamp(
        #                 int(data.get('created_time'))).isoformat(),
        #         }
        #         if data.get('transaction_type') == 'sellorder':
        #             # parsed.update({
        #             #     'phone_number': data.get('phone_number_load'),
        #             #     'network': data.get('payment_outlet_name')
        #             # })
        #             pass
        #         else:
        #             parsed['payment_method'] = data.get('payment_outlet_id')

        #         return parsed

        #     def get_user_agent(self, validated_data):
        #         # Update will be performed by worker that polls the sellorder
        #         ua_dict = self.initial_data.get('user_agent')
        #         ua_query = 'device_hash' if ua_dict.get('device_hash') else 'browser'
        #         query_dict = {ua_query: ua_dict.get(ua_query)}

        #         try:
        #             user_agent = UserAgent.objects.get(**query_dict)
        #         except UserAgent.DoesNotExist:
        #             serializer = UserAgentSerializer(
        #                 data=self.initial_data.get('user_agent'))
        #             if not serializer.is_valid():
        #                 pass
        #             user_agent = serializer.create(serializer.validated_data)
        #         finally:
        #             validated_data['user_agent'] = user_agent

        #         return validated_data

        #     def create(self, validated_data):
        #         if validated_data.get('transaction_type') is None:
        #             '''
        #             This condition will be met if create method is triggered by a POST
        #             request from a user. Remember that transaction_type is not provided
        #             in that case. See comments on __init__ method.
        #             '''
        #             return super().create(validated_data)

        #         # this is call if create method is triggered by sync_order_db on
        #         # the utility module. We need to get the user_agent value since this is
        #         # the way we identify who made the order. This case is particularly
        #         # happen if coins.ph mobile app is used
        #         data = self.get_user_agent(validated_data)
        #         return super().create(data)

        #     def update(self, instance, validated_data):
        #         # Update will be performed by worker that polls the sellorder
        #         data = self.get_user_agent(validated_data)
        #         return super().update(data)

        # class TransactionDetailSerializer(TransactionSerializer):
        #     phone_number = serializers.CharField(source='loadorder.phone_number')
        #     network = serializers.CharField(source='loadorder.network')

        #     class Meta(TransactionSerializer.Meta):
        #         fields = '__all__'

        #     def __init__(self, instance, *args, **kwargs):
        #         super(TransactionDetailSerializer, self).__init__(
        #             instance, *args, **kwargs)
        #         if instance.transaction_type == 'buy_order':
        #             self.fields.pop('phone_number')
        #             self.fields.pop('network')

        # class LoadTransactionSerializer(serializers.ModelSerializer):

        #     class Meta:
        #         model = LoadTransaction
        #         fields = '__all__'

        # class _TransactionSerializer(serializers.ModelSerializer):
        #     user_agent = UserAgentSerializer()

        #     class Meta:
        #         model = LoadTransaction
        #         fields = '__all__'

        #     def __init__(self, instance=None, data=empty, **kwargs):
        #         if data != empty and not kwargs.get('partial'):
        #             data = TransactionDetailSerializer.order_to_transactions_map(data)
        #         super().__init__(instance=instance, data=data, **kwargs)

        #     @staticmethod
        #     def order_to_transactions_map(data):
        #         parsed = {
        #             'id': data.get('id'),
        #             'confirmation_code': data.get('confirmation_code'),
        #             'account': data.get('user_id'),
        #             'user_agent': data.get('user_agent'),
        #             'transaction_type': data.get('transaction_type'),
        #             'status': data.get('delivery_status') or data.get('status'),
        #             'amount': data.get('amount') or data.get('subtotal'),
        #             'fee': data.get('currency_fees') or data.get('coins_fee'),
        #             'transaction_date': datetime.fromtimestamp(
        #                 int(data.get('created_time'))).isoformat(),
        #         }
        #         if data.get('transaction_type') == 'sellorder':
        #             parsed.update({
        #                 'phone_number': data.get('phone_number_load'),
        #                 'network': data.get('payment_outlet_name')
        #             })
        #         else:
        #             parsed['payment_method'] = data.get('payment_outlet_id')

        #         return parsed

        #     def create(self, validated_data):
        #         # Use user_agent to bind this transaction to a retailer
        #         ua_dict = self.initial_data.get('user_agent')
        #         ua_query = 'device_hash' if ua_dict.get('device_hash') else 'browser'
        #         query_dict = {ua_query: ua_dict.get(ua_query)}

        #         try:
        #             user_agent = UserAgent.objects.get(**query_dict)
        #         except UserAgent.DoesNotExist:
        #             serializer = UserAgentSerializer(
        #                 data=self.initial_data.get('user_agent'))
        #             if not serializer.is_valid():
        #                 pass
        #             user_agent = serializer.create(serializer.validated_data)
        #         finally:
        #             validated_data['user_agent'] = user_agent

        #         status = validated_data.get('status')
        #         if status == 'expired' or status == 'canceled':
        #             return super().create(validated_data)

        #         return super().create(validated_data)
