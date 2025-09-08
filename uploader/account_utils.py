# -*- coding: utf-8 -*-
"""
Account-related utility functions
"""

from .logging_utils import log_info, log_error, log_debug


def get_account_details(account, proxy=None):
    """Get account details safely in a sync context"""
    details = {
        'username': account.username,
        'password': account.password,
        'tfa_secret': account.tfa_secret,
        'email_login': getattr(account, 'email_username', None),
        'email_password': getattr(account, 'email_password', None)
    }
    
    # Add proxy information if available
    if proxy:
        proxy_details = get_proxy_details(proxy)
        if proxy_details:
            details['proxy'] = {
                'type': 'http',  # Default type
                'host': proxy_details['host'],
                'port': proxy_details['port'],
                'user': proxy_details['username'],
                'pass': proxy_details['password']
            }
    
    # Locale and language mapping
    try:
        loc = getattr(account, 'locale', None) or 'ru_BY'
    except Exception:
        loc = 'ru_BY'
    details['locale'] = loc
    try:
        lang = (loc.split('_', 1)[0] or 'ru').lower()
        if lang not in ('en','ru','es','pt'):
            lang = 'ru'
    except Exception:
        lang = 'ru'
    details['language'] = lang

    return details


def get_proxy_details(proxy):
    """Get proxy details safely in a sync context"""
    if not proxy:
        return None
    return {
        'host': proxy.host,
        'port': proxy.port,
        'username': proxy.username,
        'password': proxy.password
    }


def get_account_proxy(account_task, account):
    """Get proxy from account or account_task in a sync context"""
    return account_task.proxy or account.proxy


def get_account_dolphin_profile_id(account):
    """Get Dolphin Anty profile ID from account in a sync context"""
    return account.dolphin_profile_id


def save_dolphin_profile_id(account, profile_id):
    """Save Dolphin Anty profile ID to account in a sync context"""
    log_info(f"Saving Dolphin profile ID {profile_id} to account {account.username}")
    account.dolphin_profile_id = profile_id
    account.save(update_fields=['dolphin_profile_id'])
    return account 