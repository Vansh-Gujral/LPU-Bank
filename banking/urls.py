from django.urls import path
from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views

urlpatterns = [
    # --- 1. UI PAGE ROUTES ---
    path('', TemplateView.as_view(template_name='banking/index.html'), name='home'),
    path('login/', TemplateView.as_view(template_name='banking/login.html'), name='login'),
    path('signup/', TemplateView.as_view(template_name='banking/signup.html'), name='signup'),
    path('dashboard/', TemplateView.as_view(template_name='banking/dashboard.html'), name='dashboard'),
    path('transfer/', TemplateView.as_view(template_name='banking/transfer.html'), name='transfer'),
    path('atm-request/', TemplateView.as_view(template_name='banking/atm_request.html'), name='atm_request'),
    path('claim-deposit/', TemplateView.as_view(template_name='banking/claim_deposit.html'), name='claim_deposit'),
    path('set-pin/', TemplateView.as_view(template_name='banking/set_pin.html'), name='set_pin'),
    path('api/my-qr/', views.get_my_qr, name='my-qr'),
    path('qr/', lambda req: render(req, 'banking/qr.html'), name='qr'),

    # --- 2. API ENDPOINTS ---
    # Authentication (JWT)
    path('api/login/', TokenObtainPairView.as_view(), name='api_login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('api/register/', views.register_user, name='api_register'),

    # Banking Operations (Stateless/Protected)
    path('api/dashboard/', views.DashboardAPIView.as_view(), name='api_dashboard'),
    path('api/transfer/', views.transfer_money, name='api_transfer'),
    path('api/set-pin/', views.set_pin, name='api_set_pin'),
    path('api/token-status/<str:token>/', views.check_token_status, name='api_token_status'),

    # --- Razorpay API Routes ---
    path('api/deposit/initiate/', views.initiate_payment, name='api_initiate_payment'),
    path('api/deposit/callback/', views.payment_callback, name='api_payment_callback'),

    # --- Razorpay UI Routes ---
    path('deposit/success/', TemplateView.as_view(template_name='banking/payment_success.html'), name='payment_success'),
    path('deposit/failure/', TemplateView.as_view(template_name='banking/payment_failure.html'), name='payment_failure'),

    # ATM & Deposit
    path('api/atm-request/', views.generate_atm_token, name='api_atm_request'),
    path('api/claim-deposit/', views.claim_deposit, name='api_claim_deposit'),

    # Razorpay & PDF
    path('api/deposit/initiate/', views.initiate_payment, name='api_initiate_payment'),
    path('api/deposit/callback/', views.payment_callback, name='api_payment_callback'),
    path('api/download-statement/', views.download_statement, name='api_download_statement'),
]