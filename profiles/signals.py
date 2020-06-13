from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from profiles.models import Profile


USER_MODEL = get_user_model()


@receiver(post_save, sender=USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        Profile.objects.create(user=instance)