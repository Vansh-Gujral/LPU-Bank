from django.urls import path
from . import views
urlpatterns = [
    path('terminal/', views.atm_terminal, name='atm_terminal'),
    path('deposit/', views.atm_deposit, name='atm_deposit'),
]