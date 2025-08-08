import time
import logging
import os

logger = logging.getLogger('uploader.middleware')
SILENT_REQUEST_LOGS = os.getenv('SILENT_REQUEST_LOGS') == '1'

class RequestLoggingMiddleware:
    """Middleware to log all requests (can be silenced via env)"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        start_time = time.time()
        log_prefix = f"[{request.method}]"
        
        # Log request details
        user_info = f"User: {request.user}" if request.user.is_authenticated else "User: Anonymous"
        msg_req = f"{log_prefix} Request received: {request.path} - {user_info}"
        if SILENT_REQUEST_LOGS:
            logger.info(msg_req)
        else:
            print(msg_req)
        
        # Process request
        response = self.get_response(request)
        
        # Log response details
        duration = round((time.time() - start_time) * 1000)
        msg_resp = f"{log_prefix} Response: {request.path} - Status: {response.status_code} - Duration: {duration}ms"
        if SILENT_REQUEST_LOGS:
            logger.info(msg_resp)
        else:
            print(msg_resp)
        
        return response 