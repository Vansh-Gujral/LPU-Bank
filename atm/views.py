from django.shortcuts import render
from .models import ATMToken
from banking.models import Transaction, Account
from django.db import transaction
from decimal import Decimal
import random

def atm_terminal(request):
    """
    Simulates an ATM Machine for WITHDRAWALS.
    User enters a token generated from their Bank Dashboard.
    """
    error = None
    success_msg = None
    
    if request.method == "POST":
        user_token = request.POST.get('token')
        try:
            token_obj = ATMToken.objects.get(token=user_token, is_used=False)
            if hasattr(token_obj, 'is_expired') and token_obj.is_expired():
                error = "This token has expired. Please generate a new one."
            else:
                with transaction.atomic():
                    account = token_obj.account
                    
                    if account.balance < token_obj.amount:
                        error = "Insufficient funds in the linked account."
                    else:
                        account.balance -= token_obj.amount
                        account.save()
                        
                        token_obj.is_used = True
                        token_obj.save()
                        
                        Transaction.objects.create(
                            sender=account,
                            amount=token_obj.amount,
                            transaction_type='ATM_WITHDRAW',
                            status='SUCCESS',
                            description=f"ATM Cash Out - Token {user_token}"
                        )
                        success_msg = f"Please collect your cash: ₹{token_obj.amount}"
                        
        except ATMToken.DoesNotExist:
            error = "Invalid Token. Please check and try again."
        except Exception as e:
            error = f"An unexpected error occurred: {str(e)}"

    return render(request, 'atm/terminal.html', {'error': error, 'success_msg': success_msg})


def atm_deposit(request):
    """
    Simulates an ATM Machine for DEPOSITS.
    Generates a code that the user must 'Claim' in their Bank Dashboard.
    """
    ref_code = None
    amount = None
    error = None

    if request.method == "POST":
        amount_str = request.POST.get('amount')
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive.")

            ref_code = str(random.randint(100000, 999999))
            
            ATMToken.objects.create(
                token=ref_code,
                amount=amount,
                is_used=False
            )
            
            return render(request, 'atm/deposit_form.html', {
                'ref_code': ref_code, 
                'amount': amount
            })
            
        except (ValueError, Decimal.InvalidOperation):
            error = "Invalid amount entered. Please enter a valid number."
        except Exception as e:
            error = f"Error generating deposit code: {str(e)}"

    return render(request, 'atm/deposit_form.html', {'error': error})