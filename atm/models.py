from django.db import models
from banking.models import Account
from django.utils import timezone
import datetime

class ATMToken(models.Model):
    account = models.ForeignKey('banking.Account', on_delete=models.CASCADE, null=True, blank=True)
    token = models.CharField(max_length=6, unique=True) 
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + datetime.timedelta(minutes=15)

    def __str__(self):
        return f"Token for {self.account.user.username} - {self.token}"