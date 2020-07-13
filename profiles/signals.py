from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from profiles.models import Profile, SummaryCard


USER_MODEL = get_user_model()
retailers = Group.objects.get_or_create(name='retailers')[0]
retailer_cards = [
    {
        'name': 'sales',
        'color': 'primary',
        'is_dark': True
    },
    {
        'name': 'rebates',
        'color': 'primary',
        'is_dark': True
    },
    {
        'name': 'top_ups',
        'color': 'primary',
        'is_dark': True
    },
]


@receiver(post_save, sender=USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        profile = Profile.objects.create(user=instance)
        profile.user.groups.add(retailers)
        for card in retailer_cards:
            SummaryCard.objects.create(retailer=profile, **card)
