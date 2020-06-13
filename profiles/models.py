from django.db import models
from django.contrib.auth import get_user_model
from cphapp.models import UserAgent

USER_MODEL = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(
        USER_MODEL, on_delete=models.CASCADE, null=True)
    user_agent = models.ForeignKey(
        UserAgent, on_delete=models.SET_NULL, null=True)
    bio = models.CharField(max_length=150, null=True)
    avatar = models.ImageField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username
