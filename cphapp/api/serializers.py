from datetime import datetime
from django.utils.timezone import get_current_timezone
from rest_framework import serializers
from cphapp.models import Transactions
from cphapp.models import SellLoadOrder
from cphapp.utils import utc_to_local
from cph.coinsph import get_sell_order

# 10 minutes. Maybe this should live inside the settings.py
TDELTA_MAX = 10 * 60


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transactions
        fields = '__all__'

    def validate(self, attrs):

        if attrs.get('transaction_type') == 'buy':
            return super().validate(attrs)

        # Validate combined reward and sell
        reward_amount = attrs.get('reward_amount')
        balance_after_reward = attrs.get('running_balance')
        balance_before_reward = self.initial_data.get(
            'balance_before_reward')
        calculated_balance = balance_before_reward + reward_amount

        try:
            assert calculated_balance == balance_after_reward
        except AssertionError:
            raise serializers.ValidationError(
                ('Running balance before and after reward is not as expected! '
                    f'calculated_balance ({balance_before_reward + reward_amount})'
                    f' != actual_balance ({balance_after_reward})'))

        # Validate time delta between sell and reward doesn't exceed limit
        reward_created_at = attrs.get('transaction_date')
        sell_created_at = self.initial_data.get('sell_transaction_date')[:-1]
        sell_created_at = utc_to_local(datetime.fromisoformat(
            sell_created_at), get_current_timezone())
        tdelta = (reward_created_at - sell_created_at).total_seconds()

        try:
            assert tdelta < TDELTA_MAX
        except AssertionError:
            raise serializers.ValidationError(
                ('Time delta between reward and sell transactions exceeded the'
                    f' limit ({TDELTA_MAX / 60}) minutes:'
                    f' tdelta ({tdelta / 60})'))
        else:
            return super().validate(attrs)


class TransactionDetailSerializer(TransactionSerializer):
    order = serializers.SerializerMethodField()

    def get_order(self, obj):
        order = get_sell_order(id='5fe3c5b0763e4bfdae9ed46b6546e0eb')
        phone_number = order['order']['phone_number_load']
        network = order['order']['payment_account']['payment_outlet']['name']
        return {
            'phone_number': phone_number,
            'network': network
        }


class SellOrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = SellLoadOrder
        fields = '__all__'
