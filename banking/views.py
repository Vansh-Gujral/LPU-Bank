from django.contrib.auth.hashers import make_password, check_password 
from django.db import transaction, models
from .models import Transaction, Account
from atm.models import ATMToken
import random
from decimal import Decimal 
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from .forms import UserRegistrationForm
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from .serializers import AccountSerializer, TransactionSerializer, TransferRequestSerializer, UserRegisterSerializer
import qrcode

client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_dashboard_data(request):
    account = request.user.account
    return Response({
        "username": request.user.username,
        "balance": str(account.balance),
        "account_number": account.account_number
    })


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = request.user.account
        recent_tx = Transaction.objects.filter(
            models.Q(sender=account) | models.Q(receiver=account)
        ).order_by('-timestamp')[:10]
        account_data = AccountSerializer(account).data
        transaction_data = TransactionSerializer(recent_tx, many=True).data

        return Response({
            "account": account_data,
            "transactions": transaction_data
        })

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserRegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            "status": "success",
            "message": "User and Account nodes successfully initialized."
        }, status=201)
    
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def manual_login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })
    
    return Response({"error": "Invalid Credentials"}, status=401)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_pin(request):
    account = request.user.account
    pin1 = request.data.get('pin1')
    pin2 = request.data.get('pin2')
    
    if pin1 != pin2:
        return Response({"error": "PINs do not match!"}, status=400)
    elif not pin1 or len(pin1) != 6 or not pin1.isdigit():
        return Response({"error": "PIN must be exactly 6 digits."}, status=400)
    
    account.transaction_pin = make_password(pin1)
    account.save()
    return Response({"message": "Transaction PIN updated successfully!"})


from .serializers import TransferRequestSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transfer_money(request):
    serializer = TransferRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data
    sender_account = request.user.account
    
    if not check_password(data['pin'], sender_account.transaction_pin):
        return Response({"error": "Invalid Transaction PIN."}, status=403)
    if sender_account.balance < data['amount']:
        return Response({"error": "Insufficient funds."}, status=400)

    try:
        receiver_acc = None
        if data['type'] == "UPI":
            receiver_acc = Account.objects.get(upi_id=data['receiver_detail'])
        elif data['type'] == "ACC":
            receiver_acc = Account.objects.get(account_number=data['receiver_detail'])
        elif data['type'] == "MOBILE":
            receiver_acc = Account.objects.get(user__phone_number=data['receiver_detail'])

        if sender_account == receiver_acc:
            return Response({"error": "Self-transfers are not permitted."}, status=400)

        with transaction.atomic():
            sender_account.balance -= data['amount']
            receiver_acc.balance += data['amount']
            sender_account.save()
            receiver_acc.save()

            Transaction.objects.create(
                sender=sender_account,
                receiver=receiver_acc,
                amount=data['amount'],
                transaction_type=data['type'],
                status='SUCCESS',
                description=f"API Transfer to {data['receiver_detail']}"
            )

        return Response({"message": "Transfer successful"}, status=200)

    except Account.DoesNotExist:
        return Response({"error": "Receiver not found."}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_atm_token(request):

    account = request.user.account
    amount_str = request.data.get('amount')
    pin = request.data.get('pin')
    if not amount_str or not pin:
        return Response({"error": "Amount and Transaction PIN are required."}, status=400)

    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            return Response({"error": "Invalid amount. Must be greater than zero."}, status=400)

        if not check_password(pin, account.transaction_pin):
            return Response({"error": "Invalid Transaction PIN."}, status=403)

        if account.balance < amount:
            return Response({"error": "Insufficient balance for this request."}, status=400)

        token = str(random.randint(100000, 999999))
        ATMToken.objects.create(account=account, token=token, amount=amount)

        return Response({
            "message": "ATM Token generated successfully.",
            "token": token,
            "amount": str(amount),
            "expiry": "Valid for 15 minutes" 
        }, status=201)

    except ValueError:
        return Response({"error": "Invalid amount format."}, status=400)
    except Exception as e:
        return Response({"error": f"Internal server error: {str(e)}"}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_deposit(request):
    account = request.user.account
    ref_code = request.data.get('ref_code')

    if not ref_code:
        return Response({"error": "Reference code is required."}, status=400)

    try:
        token_obj = ATMToken.objects.get(token=ref_code, is_used=False)

        with transaction.atomic():
            account.balance += token_obj.amount
            account.save()

            token_obj.is_used = True
            token_obj.save()

            Transaction.objects.create(
                receiver=account,
                amount=token_obj.amount,
                transaction_type='ATM_DEPOSIT',
                status='SUCCESS',
                description=f"Cash Deposit Claimed | Ref: {ref_code}"
            )

        return Response({
            "message": "Deposit claimed successfully.",
            "credited_amount": str(token_obj.amount),
            "new_balance": str(account.balance)
        }, status=200)

    except ATMToken.DoesNotExist:
        return Response({"error": "Invalid or already used reference code."}, status=404)
    except Exception as e:
        return Response({"error": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_token_status(request, token):
    try:
        token_obj = ATMToken.objects.get(token=token, account=request.user.account)
        return Response({
            "is_used": token_obj.is_used,
            "amount": str(token_obj.amount)
        })
    except ATMToken.DoesNotExist:
        return Response({"error": "Token not found"}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    try:
        amount_inr = Decimal(request.data.get('amount', 10))
        amount_paise = int(amount_inr * 100)
        data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"receipt_{request.user.id}_{random.randint(1000, 9999)}",
            "payment_capture": 1,
            "notes": {
                "user_id": str(request.user.id)
            }
        }

        razorpay_order = client.order.create(data=data)
        
        return Response({
            "order_id": razorpay_order['id'],
            "razorpay_merchant_key": settings.RAZOR_KEY_ID,
            "amount": amount_paise,
            "currency": "INR",
            "user_name": request.user.username,
            # "user_email": request.user.email
            "user_email": request.user.email if request.user.email else f"{request.user.username}@test.com"
        }, status=201)
        
    except Exception as e:
        return Response({"error": f"Razorpay Error: {str(e)}"}, status=500)
    
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def payment_callback(request):
    params_dict = {
        'razorpay_order_id': request.data.get('razorpay_order_id'),
        'razorpay_payment_id': request.data.get('razorpay_payment_id'),
        'razorpay_signature': request.data.get('razorpay_signature')
    }

    try:
        client.utility.verify_payment_signature(params_dict)
        order_details = client.order.fetch(params_dict['razorpay_order_id'])
        user_id = int(order_details['notes']['user_id'])
        
        from .models import User 
        user = User.objects.get(id=user_id)
        amount_inr = Decimal(order_details['amount']) / 100

        with transaction.atomic():
            account = user.account
            account.balance += amount_inr
            account.save()

            Transaction.objects.create(
                receiver=account,
                amount=amount_inr,
                transaction_type='DEPOSIT',
                status='SUCCESS',
                description=f"Razorpay Deposit | ID: {params_dict['razorpay_payment_id']}"
            )

        return Response({"message": "Payment successful and balance updated."}, status=200)

    except razorpay.errors.SignatureVerificationError:
        return Response({"error": "Signature verification failed."}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
    

@api_view(['GET'])
@permission_classes([AllowAny])  
def download_statement(request):
    user_id = request.query_params.get('uid')
    if not user_id:
        return Response({"error": "Authentication token missing."}, status=401)

    try:
        from .models import User
        user = User.objects.get(id=user_id)
        account = user.account
        
        transactions = Transaction.objects.filter(
            models.Q(sender=account) | models.Q(receiver=account)
        ).order_by('-timestamp')

        data = {
            'account': account,
            'transactions': transactions,
            'user': user,
        }
        template = get_template('banking/statement_pdf.html')
        html = template.render(data)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Statement_{account.account_number}.pdf"'
            return response
            
        return Response({"error": "PDF Generation failed"}, status=500)
        
    except User.DoesNotExist:
        return Response({"error": "Invalid User"}, status=404)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_qr(request):
    account = request.user.account
    upi_data = f"upi://pay?pa={account.upi_id}&pn={request.user.username}&cu=INR"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#10b981", back_color="#0f172a")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')