from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import UserProfile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile for every User so /profile/ never 404s."""
    UserProfile.objects.get_or_create(user=instance)
