#!/usr/bin/env python
"""
SSL Fix Module - Resolves SSL errors with proxies
This module should be imported at the very beginning of the application
"""

import os
import ssl
import urllib3
import warnings
import logging

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('scripts.ssl_fix')

def apply_ssl_fix():
    """Apply SSL fixes for proxy compatibility"""
    try:
        # Disable SSL warnings globally
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Set default SSL context to not verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Apply to default SSL context
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # Also set environment variables for requests library
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        os.environ['CURL_CA_BUNDLE'] = ''
        
        print("[SSL_FIX] SSL verification disabled globally for proxy compatibility")
        return True
        
    except Exception as e:
        print(f"[SSL_FIX] Warning: Could not apply SSL fixes: {e}")
        return False

def configure_requests_session(session):
    """Configure a requests session to disable SSL verification"""
    try:
        session.verify = False
        session.proxies = getattr(session, 'proxies', {})
        return True
    except Exception as e:
        print(f"[SSL_FIX] Warning: Could not configure session: {e}")
        return False

# Apply fixes immediately when module is imported
apply_ssl_fix()
