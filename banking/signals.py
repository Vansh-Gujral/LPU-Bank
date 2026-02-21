from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Account

# @receiver(post_save, sender=User)
# def create_user_account(sender, instance, created, **kwargs):
#     if created:
#         # Automatically create an Account object for the new user
#         Account.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_account(sender, instance, created, **kwargs):
    if created:
        # Only CREATE — don't try to save, it's brand new
        Account.objects.get_or_create(user=instance)
    else:
        # Only save if account already exists
        if hasattr(instance, 'account'):
            instance.account.save()