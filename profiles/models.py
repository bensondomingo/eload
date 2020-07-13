from django.db import models
from django.contrib.auth import get_user_model
from cphapp.models import UserAgent

USER_MODEL = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(
        USER_MODEL, on_delete=models.CASCADE, null=True)
    user_agent = models.ForeignKey(
        UserAgent, on_delete=models.SET_NULL, null=True, blank=True)
    bio = models.CharField(max_length=150, null=True)
    avatar = models.ImageField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.get_username()


class SummaryCard(models.Model):
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
