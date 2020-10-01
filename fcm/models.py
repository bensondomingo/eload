from django.db import models
from profiles.models import Profile as Retailer


class FCMDevice(models.Model):
    token = models.CharField(max_length=250)
    owner = models.ForeignKey(
        Retailer, related_name='fcmdevices', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('owner',)

    def __str__(self):
        return f'{self.owner}: {self.token[:25]} ...'
