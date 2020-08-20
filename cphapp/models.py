from uuid import uuid4
from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField
from django.contrib.auth import get_user_model
from django.utils.timezone import get_current_timezone

from cphapp.utils import utc_to_local

USER_MODEL = get_user_model()


def get_sentinel_user():
    return USER_MODEL.objects.get_or_create(username='deleted')[0]


class UserAgent(models.Model):
    device = models.CharField(max_length=50)
    platform = models.CharField(max_length=50)
    browser = models.CharField(max_length=50, blank=True)
    appsflyer_id = models.CharField(max_length=50, blank=True)
    device_hash = models.CharField(max_length=70, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f'{self.platform} - {self.device} - {self.browser}'


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
        verbose_name_plural = 'transactions'
        ordering = ('-transaction_date',)

    # Identity fields
    id = models.UUIDField(primary_key=True, default=uuid4)
    order_id = models.CharField(max_length=50, null=True, blank=True)
    confirmation_code = models.CharField(max_length=50, null=True, blank=True)
    account = models.CharField(max_length=100, null=True, blank=True)

    # Used to distinguish transaction owner
    retailer = models.ForeignKey(
        USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    user_agent = models.ForeignKey(
        UserAgent, on_delete=models.SET_NULL, null=True, blank=True)

    # Used to determine balance
    transaction_type = models.CharField(max_length=10, default='sellorder')
    status = models.CharField(max_length=20, null=True, blank=True)
    amount = models.FloatField()

    posted_amount = models.FloatField(default=0, blank=True)
    running_balance = models.FloatField(null=True, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)

    # sellorder
    phone_number = models.CharField(max_length=13, blank=True, null=True)

    # buyorder
    payment_method = models.CharField(max_length=50, blank=True, null=True)

    # new fields
    outlet_id = models.CharField(max_length=15, blank=True, null=True)
    product_code = models.CharField(max_length=20, default='regular')
    error = models.TextField(blank=True, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        transaction_date = utc_to_local(
            self.created_at, get_current_timezone())
        transaction_date = transaction_date.strftime('%Y-%m-%d %I:%M %p')

        if self.status is None:
            return f'{self.phone_number} - {self.amount} - {self.product_code}'

        return (f'{self.confirmation_code} - {transaction_date} - '
                f'{self.transaction_type} - {self.amount}')

    @property
    def complete(self):
        return self.running_balance is not None

    @property
    def sold_this_month(self):
        return LoadTransaction.objects.filter(
            status='settled',
            transaction_date__month=self.created_at.month,
            transaction_date__year=self.created_at.year).aggregate(
                amount=models.Sum('amount')).get('amount')

    @property
    def reward_amount(self):
        if self.status != 'settled' or self.transaction_type == 'buyorder':
            return 0

        sold_this_month = LoadTransaction.objects.filter(
            status='settled',
            transaction_date__month=self.created_at.month,
            transaction_date__year=self.created_at.year).aggregate(
                amount=models.Sum('amount')).get('amount')
        reward_factor = 0.1 if sold_this_month <= 10e3 else 0.05
        return self.amount * reward_factor

    @property
    def network(self):
        if self.transaction_type != 'sellorder':
            return None
        outlet = LoadOutlet.objects.get(id=self.outlet_id)
        return outlet.name


# class LoadTransaction(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
#     retailer = models.ForeignKey(
#         USER_MODEL, on_delete=models.SET(get_sentinel_user))
#     phone_number = models.CharField(max_length=13)
#     amount = models.IntegerField()
#     product_code = models.CharField(max_length=20, null=True, blank=True)
#     outlet = models.ForeignKey(
#         LoadOutlet, on_delete=models.SET_NULL, null=True, blank=True)
#     order_id = models.CharField(max_length=50, null=True, blank=True)
#     status = models.CharField(max_length=20, default='pending')

#     # From Transaction model
#     order_id = models.CharField(max_length=50)
#     confirmation_code = models.CharField(max_length=10, null=True, blank=True)
#     account = models.CharField(max_length=50, null=True, blank=True)
#     user_agent = models.ForeignKey(
#         UserAgent, on_delete=models.SET_NULL, null=True, blank=True)

#     running_balance = models.FloatField(null=True, blank=True)
#     posted_amount = models.IntegerField(default=0, null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         abstract = True

#     @property
#     def reward_amount(self):
#         if self.status not in ['settled', 'success']:
#             return 0

#         sold_this_month = self.objects.filter(
#             status='settled',
#             transaction_date__month=self.created_at.month,
#             transaction_date__year=self.created_at.year).aggregate(
#                 amount=models.Sum('amount')).get('amount')
#         reward_factor = 0.1 if sold_this_month <= 10e3 else 0.05
#         return self.amount * reward_factor

#     @property
#     def transaction_type(self):
#         return 'sellorder'
