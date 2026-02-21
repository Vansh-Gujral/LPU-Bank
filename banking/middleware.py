# banking/middleware.py
class RazorpayPermissionsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Force-delete any existing restrictive policy then set ours
        try:
            del response['Permissions-Policy']
        except KeyError:
            pass
        try:
            del response['Feature-Policy']  
        except KeyError:
            pass
            
        response['Permissions-Policy'] = "accelerometer=*, gyroscope=*, magnetometer=*, payment=*, camera=*, microphone=()"
        return response