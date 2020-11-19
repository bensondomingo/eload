from django.db import models
from django.contrib.auth import get_user_model


USER_MODEL = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(
        USER_MODEL, on_delete=models.CASCADE, null=True)
    bio = models.CharField(max_length=150, null=True)
    avatar = models.ImageField(null=True, blank=True)
    top_up_amount = models.FloatField(default=2, null=True, blank=True)
    top_up_th = models.FloatField(default=100, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_username()

    @property
    def username(self):
        return self.user.username


class SummaryCard(models.Model):
    SALES = 'sales'
    TOP_UPS = 'top_ups'
    REBATES = 'rebates'
    CASH_IN = 'cash_in'
    NAME_CHOICES = [
        (SALES, 'Sales'),
        (TOP_UPS, 'Top ups'),
        (REBATES, 'Rebates'),
        (CASH_IN, 'cash_in')
    ]

    name = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default='primary')
    is_dark = models.BooleanField(default=True)
    retailer = models.ForeignKey(Profile, on_delete=models.CASCADE,
                                 related_name='cards', blank=True, null=True)

    def __str__(self):
        return f'{self.retailer} - {self.name}'

    @property
    def title(self):
        return ' '.join(map(str.upper, self.name.split('_')))
