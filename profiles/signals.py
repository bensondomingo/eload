from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from profiles.models import Profile, SummaryCard

USER_MODEL = get_user_model()


def get_summary_cards(for_staff):

    if not for_staff:
        return [{
            'name': choice[0],
            'color': 'primary',
            'is_dark': True
        } for choice in SummaryCard.NAME_CHOICES[:2]]

    return [{
            'name': choice[0],
            'color': 'primary',
            'is_dark': True
            } for choice in SummaryCard.NAME_CHOICES[2:4]]


@receiver(post_save, sender=USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """ Create a new profile for new user instance """

    if instance.is_superuser:
        return

    if created:
        # Called when a new user is created
        profile = Profile.objects.create(user=instance)
        retailers = Group.objects.get_or_create(name='retailers')[0]
        profile.user.groups.add(retailers)
        for card in get_summary_cards(for_staff=False):
            SummaryCard.objects.create(retailer=profile, **card)
        return

    if instance.is_staff and instance.profile.cards.count() <= 2:
        for card in get_summary_cards(for_staff=True):
            SummaryCard.objects.create(retailer=instance.profile, **card)
        return
