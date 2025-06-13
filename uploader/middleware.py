import time
import logging

logger = logging.getLogger('uploader.middleware')

class RequestLoggingMiddleware:
    """Middleware to log all requests to the console"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        start_time = time.time()
        log_prefix = f"[{request.method}]"
        
        # Log request details
        user_info = f"User: {request.user}" if request.user.is_authenticated else "User: Anonymous"
        print(f"{log_prefix} Request received: {request.path} - {user_info}")
        
        # Process request
        response = self.get_response(request)
        
        # Log response details
        duration = round((time.time() - start_time) * 1000)
        print(f"{log_prefix} Response: {request.path} - Status: {response.status_code} - Duration: {duration}ms")
        
        return response 