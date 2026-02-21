from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
import uuid

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_kyc_verified = models.BooleanField(default=False)

class Account(models.Model):
    ACCOUNT_TYPES = (
        ('SAVINGS', 'Savings'),
        ('CURRENT', 'Current'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account')
    account_number = models.CharField(max_length=12, unique=True, editable=False)
    upi_id = models.CharField(max_length=50, unique=True, editable=False)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='SAVINGS')
    transaction_pin = models.CharField(max_length=128) 

    def save(self, *args, **kwargs):
        if not self.account_number:
            self.account_number = get_random_string(10, allowed_chars='0123456789')
        if not self.upi_id:
            self.upi_id = f"{self.user.username}@mybank"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('UPI', 'UPI Transfer'),
        ('ACC_TRANSFER', 'Account Transfer'),
        ('MOBILE_PAY', 'Mobile Payment'),
        ('ATM_WITHDRAW', 'ATM Withdrawal'),
        ('ATM_DEPOSIT', 'ATM Deposit'),
    )

    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    sender = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='sent_transactions', null=True, blank=True)
    receiver = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='received_transactions', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, default='SUCCESS')

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"