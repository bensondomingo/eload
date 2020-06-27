from django.db import models
from django.utils.timezone import get_current_timezone

from cphapp.utils import utc_to_local


class Transaction(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    account = models.CharField(max_length=100)
    transaction_type = models.CharField(max_length=10)
    status = models.CharField(max_length=20)
    amount = models.FloatField()
    reward_amount = models.FloatField(null=True, blank=True)
    posted_amount = models.FloatField()
    running_balance = models.FloatField()
    order_id = models.CharField(max_length=100)
    reward_id = models.CharField(max_length=100, null=True, blank=True)
    transaction_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'transactions'
        ordering = ('-transaction_date',)

    @classmethod
    def count(cls, transaction_type='all'):
        assert transaction_type in ('sell', 'buy', 'all')
        obj = cls.objects
        return obj.count() if transaction_type == 'all' else obj.filter(
            transaction_type=transaction_type).count()

    def __str__(self):
        transaction_date = utc_to_local(
            self.transaction_date, get_current_timezone())
        transaction_date = transaction_date.strftime('%Y-%m-%d %I:%M %p')

        return (f'{self.id} - {transaction_date} - {self.transaction_type} - '
                f'{self.amount}')

    @property
    def order(self):
        if self.transaction_type == 'sell_order':
            return self.load_order
        return self.buy_order

    @property
    def user_agent(self):
        if self.transaction_type == 'sell_order':
            return self.load_order.user_agent
        return self.buy_order.user_agent


class UserAgent(models.Model):
    device = models.CharField(max_length=50)
    platform = models.CharField(max_length=50)
    browser = models.CharField(max_length=50, blank=True)
    appsflyer_id = models.CharField(max_length=50, blank=True)
    device_hash = models.CharField(max_length=70, blank=True)

    def __str__(self):
        return f'{self.platform} - {self.device} - {self.browser}'


class Network(models.Model):
    outlet_id = models.CharField(max_length=50, primary_key=True)
    outlet_name = models.CharField(max_length=20)
    name = models.CharField(max_length=50)

    class Meta:
        abstract = True


class Order(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    order_type = models.CharField(max_length=20)
    amount = models.FloatField()
    status = models.CharField(max_length=50)
    fee = models.FloatField()
    user_agent = models.ForeignKey(
        UserAgent, null=True, on_delete=models.SET_NULL)
    order_date = models.DateTimeField()
    transaction = models.OneToOneField(
        Transaction, null=True, on_delete=models.SET_NULL,
        related_name='order')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # LoadOrder fields
    phone_number = models.CharField(max_length=13, blank=True, null=True)
    network = models.CharField(max_length=50, blank=True, null=True)

    # BuyOrder fields
    payment_method = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f'{self.order_type} - {self.status} - {self.phone_number} - \
            {self.amount}'
