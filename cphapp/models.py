from django.db import models
from django.utils.timezone import get_current_timezone

from cphapp.utils import utc_to_local


class Transactions(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    account = models.CharField(max_length=100)
    transaction_type = models.CharField(max_length=10)
    status = models.CharField(max_length=20)
    reward_amount = models.FloatField()
    sell_amount = models.FloatField()
    posted_amount = models.FloatField()
    buy_amount = models.FloatField()
    running_balance = models.FloatField()
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
                f'{self.sell_amount if self.sell_amount else self.buy_amount}')


class UserAgent(models.Model):
    device = models.CharField(max_length=50)
    platform = models.CharField(max_length=50)
    browser = models.CharField(max_length=50, blank=True)
    appsflyer_id = models.CharField(max_length=50, blank=True)
    device_hash = models.CharField(max_length=70, blank=True)


class Network(models.Model):
    outlet_id = models.CharField(max_length=50, primary_key=True)
    outlet_name = models.CharField(max_length=20)
    name = models.CharField(max_length=50)

    class Meta:
        abstract = True


class Order(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    amount = models.FloatField()
    status = models.CharField(max_length=50)
    fee = models.FloatField()
    user_agent = models.ForeignKey(
        UserAgent, null=True, on_delete=models.SET_NULL)
    order_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-order_date']


class SellLoadOrder(Order):
    phone_number = models.CharField(max_length=13)
    network = models.CharField(max_length=50, blank=True)
    payment_id = models.CharField(max_length=50, blank=True)
    reward_id = models.CharField(max_length=50, blank=True)

    class Meta(Order.Meta):
        verbose_name = 'sell load order'
        verbose_name_plural = 'sell load orders'

    def __str__(self):
        return f'{self.status} - {self.phone_number} - {self.amount}'
