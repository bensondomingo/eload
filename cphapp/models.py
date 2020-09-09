import os
from uuid import uuid4
from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField
from django.utils.timezone import get_current_timezone
from django.conf import settings

from cphapp.utils import utc_to_local
from profiles.models import Profile as Retailer


class Device(models.Model):
    owner = models.ForeignKey(
        Retailer, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='devices')
    device = models.CharField(max_length=50)
    platform = models.CharField(max_length=50)
    browser = models.CharField(max_length=50, blank=True)
    appsflyer_id = models.CharField(max_length=50, blank=True)
    device_hash = models.CharField(max_length=70, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.user_agent


class LoadOutlet(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=30)
    phone_number_prefixes = ArrayField(
        base_field=models.CharField(max_length=6), default=list)
    outlet_category = models.CharField(max_length=20)
    logo_url = models.URLField()
    amount_limits = JSONField()
    denominations = JSONField()
    products = JSONField()
    custom_allowed = models.BooleanField(default=False)

    def __str__(self):
        return self.id

    def categories(self):
        pass


class LoadTransaction(models.Model):
    """ Model derived from coins.ph order data. """

    class Meta:
        verbose_name_plural = 'Load transactions'
        ordering = ('-transaction_date',)

    # Identity fields
    id = models.UUIDField(primary_key=True, default=uuid4)
    order_id = models.CharField(
        max_length=50, null=True, blank=True, unique=True)
    confirmation_code = models.CharField(max_length=50, null=True, blank=True)
    account = models.CharField(max_length=100, null=True, blank=True)

    # Used to distinguish transaction owner
    retailer = models.ForeignKey(
        Retailer, on_delete=models.SET_NULL, blank=True,
        null=True, related_name='load_transactions')
    device = models.ForeignKey(
        Device, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='load_transactions')

    # Used to determine balance
    transaction_type = models.CharField(max_length=10, default='sellorder')
    status = models.CharField(max_length=20, null=True, blank=True)
    amount = models.FloatField()

    posted_amount = models.FloatField(default=0, null=True, blank=True)
    running_balance = models.FloatField(null=True, blank=True)
    reward_amount = models.FloatField(default=0, null=True, blank=True)
    top_up_amount = models.FloatField(default=0, null=True, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)

    # sellorder
    phone_number = models.CharField(max_length=13, null=True, blank=True)

    # buyorder
    payment_method = models.CharField(max_length=50, null=True, blank=True)

    # new fields
    outlet_id = models.CharField(max_length=30, blank=True, null=True)
    product_code = models.CharField(max_length=20, default='regular')
    error = models.TextField(blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        transaction_date = utc_to_local(
            self.transaction_date, get_current_timezone())
        transaction_date = transaction_date.strftime('%Y-%m-%d %I:%M %p')

        if self.status is None:
            return f'{self.phone_number} - {self.amount} - {self.product_code}'

        return (f'{self.confirmation_code} - {transaction_date} - '
                f'{self.transaction_type} - {self.amount}')

    @property
    def is_complete(self):
        return self.running_balance is not None

    @property
    def sold_this_month(self):
        transaction_date = utc_to_local(
            self.transaction_date, get_current_timezone())
        sold_this_month = LoadTransaction.objects.filter(
            status='settled',
            transaction_date__year=transaction_date.year,
            transaction_date__month=transaction_date.month,
            transaction_date__lte=transaction_date).aggregate(
            amount=models.Sum('amount')).get('amount')

        return sold_this_month if sold_this_month is not None else 0

    @property
    def balance(self):
        if self.running_balance is None:
            return None
        return self.running_balance + self.reward_amount

    @property
    def network(self):
        if self.transaction_type != 'sellorder':
            return None
        outlet = LoadOutlet.objects.get(id=self.outlet_id)
        return outlet.name

    def save(self, *args, **kwargs):
        if self.transaction_type == 'sellorder' and self.status == 'settled':

            # Set top_up_amount value
            if self.retailer is not None:
                # Use retailer settings
                if self.top_up_amount == 0 \
                        and self.amount < self.retailer.top_up_th:
                    self.top_up_amount = self.retailer.top_up_amount
            else:
                # Apply defaults
                if self.top_up_amount == 0 and self.amount < 100:
                    self.top_up_amount = 2

            # Set reward_amount value
            if self.running_balance is not None and self.reward_amount == 0:
                reward_th = os.getenv('LOADNINJA_REWARD_TH',
                                      settings.LOADNINJA_REWARD_TH)
                reward_factor = reward_th['reward_factor'] \
                    if self.sold_this_month <= reward_th['limit'] \
                    else reward_th['reward_factor_onwards']
                self.reward_amount = self.amount * reward_factor
                self.running_balance += self.reward_amount

        super().save(*args, **kwargs)
