from rest_framework import serializers
from decimal import Decimal
from .models import Account, Transaction, User
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.contrib.auth.hashers import make_password

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    transaction_pin = serializers.CharField(write_only=True, max_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password1', 'password2', 'transaction_pin']

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        if User.objects.filter(phone_number=data['phone_number']).exists():
            raise serializers.ValidationError({"phone_number": "A user with this phone number already exists."})

        pin = data.get('transaction_pin', '')
        if not pin.isdigit() or len(pin) != 6:
            raise serializers.ValidationError({"transaction_pin": "PIN must be exactly 6 digits."})

        return data

    def create(self, validated_data):
        password = validated_data.pop('password1')
        validated_data.pop('password2')
        pin = validated_data.pop('transaction_pin')
        phone = validated_data.get('phone_number')

        with db_transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data.get('email', ''),
                password=password,
                phone_number=phone
            )
            account = user.account
            account.transaction_pin = make_password(pin)
            account.save()

        return user


class AccountSerializer(serializers.ModelSerializer):
    user = UserRegisterSerializer(read_only=True)

    class Meta:
        model = Account
        fields = ['account_number', 'balance', 'upi_id', 'user']


class TransactionSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.user.username', read_only=True)
    receiver_name = serializers.CharField(source='receiver.user.username', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'sender_name', 'receiver_name', 'amount', 'transaction_type', 'status', 'timestamp', 'description']


class TransferRequestSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['UPI', 'ACC', 'MOBILE'])
    receiver_detail = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('1.00'))
    pin = serializers.CharField(min_length=6, max_length=6)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

