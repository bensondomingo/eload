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
