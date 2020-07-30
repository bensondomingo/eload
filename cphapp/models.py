from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import get_current_timezone

from cphapp.utils import utc_to_local

USER_MODEL = get_user_model()


class UserAgent(models.Model):
    device = models.CharField(max_length=50)
    platform = models.CharField(max_length=50)
    browser = models.CharField(max_length=50, blank=True)
    appsflyer_id = models.CharField(max_length=50, blank=True)
    device_hash = models.CharField(max_length=70, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f'{self.platform} - {self.device} - {self.browser}'


class Transaction(models.Model):
    """ Model derived from coins.ph order data. """

    class Meta:
        verbose_name_plural = 'transactions'
        ordering = ('-transaction_date',)

    id = models.CharField(max_length=100, primary_key=True)
    confirmation_code = models.CharField(max_length=50)
    account = models.CharField(max_length=100)
    retailer = models.ForeignKey(
        USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    user_agent = models.ForeignKey(
        UserAgent, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=20)
    status = models.CharField(max_length=50)
    amount = models.FloatField()
    reward_amount = models.FloatField(default=0, blank=True)
    posted_amount = models.FloatField(default=0, blank=True)
    running_balance = models.FloatField(null=True, blank=True)
    fee = models.FloatField()
    transaction_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # sellorder
    phone_number = models.CharField(max_length=13, blank=True, null=True)
    network = models.CharField(max_length=50, blank=True, null=True)

    # buyorder
    payment_method = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        transaction_date = utc_to_local(
            self.transaction_date, get_current_timezone())
        transaction_date = transaction_date.strftime('%Y-%m-%d %I:%M %p')

        return (f'{self.confirmation_code} - {transaction_date} - '
                f'{self.transaction_type} - {self.amount}')

    @property
    def complete(self):
        return self.running_balance is not None


class Network(models.Model):
    outlet_id = models.CharField(max_length=50, primary_key=True)
    outlet_name = models.CharField(max_length=20)
    name = models.CharField(max_length=50)

    class Meta:
        abstract = True
