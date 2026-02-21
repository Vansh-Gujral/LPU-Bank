from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from .models import User

class BankingAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
            
            if user.check_password(password):
                return user
            
            if hasattr(user, 'account') and user.account.transaction_pin:
                if check_password(password, user.account.transaction_pin):
                    return user
                    
        except User.DoesNotExist:
            return None
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

