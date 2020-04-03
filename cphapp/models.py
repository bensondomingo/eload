from django.db import models

class Transactions(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    account = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    reward_amount = models.FloatField(null=True, blank=True)
    eload_amount = models.FloatField()
    created_at = models.DateTimeField()


