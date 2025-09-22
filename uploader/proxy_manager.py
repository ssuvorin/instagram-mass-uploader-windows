"""
Enhanced Proxy Management System
Handles automatic proxy switching on Instagram blocks/challenges
"""

import logging
import time
import random
from typing import Optional, Dict, List, Tuple
from django.utils import timezone
from django.db import transaction

from .models import Proxy, InstagramAccount
from .utils import validate_proxy

logger = logging.getLogger(__name__)

class ProxyManager:
    """Enhanced proxy management with automatic switching on blocks"""
    
    def __init__(self):
        self.blocked_proxies = {}  # Track blocked proxies per account
        self.last_proxy_switch = {}  # Track last switch time per account
        self.proxy_usage_count = {}  # Track usage count per proxy
        
    def mark_proxy_blocked(self, proxy: Proxy, account: InstagramAccount, reason: str = "blocked"):
        """Mark a proxy as blocked and update its status"""
        try:
            with transaction.atomic():
                # Update proxy status
                proxy.status = 'banned'
                proxy.last_checked = timezone.now()
                proxy.notes = f"Blocked on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}: {reason}"
                proxy.save(update_fields=['status', 'last_checked', 'notes'])
                
                # Track in memory
                proxy_key = f"{proxy.host}:{proxy.port}"
                self.blocked_proxies[proxy_key] = {
                    'blocked_at': timezone.now(),
                    'account': account.username,
                    'reason': reason
                }
                
                logger.warning(f"[PROXY_MANAGER] Marked proxy {proxy_key} as blocked for {account.username}: {reason}")
                
        except Exception as e:
            logger.error(f"[PROXY_MANAGER] Error marking proxy as blocked: {e}")
    
    def get_available_proxy(self, account: InstagramAccount, exclude_blocked: bool = True) -> Optional[Proxy]:
        """Get an available proxy for the account, excluding blocked ones"""
        try:
            # Get current proxy
            current_proxy = account.current_proxy
            
            # If current proxy is not blocked and still active, use it
            if current_proxy and current_proxy.is_active and current_proxy.status == 'active':
                if not exclude_blocked or not self._is_proxy_blocked(current_proxy):
                    return current_proxy
            
            # Find alternative proxy
            available_proxies = self._get_available_proxies(account, exclude_blocked)
            
            if not available_proxies:
                logger.error(f"[PROXY_MANAGER] No available proxies for {account.username}")
                return None
            
            # Select best proxy (prefer same region, then random)
            selected_proxy = self._select_best_proxy(available_proxies, account)
            
            if selected_proxy:
                # Update account's proxy
                account.current_proxy = selected_proxy
                account.save(update_fields=['current_proxy'])
                
                logger.info(f"[PROXY_MANAGER] Assigned new proxy {selected_proxy.host}:{selected_proxy.port} to {account.username}")
                
            return selected_proxy
            
        except Exception as e:
            logger.error(f"[PROXY_MANAGER] Error getting available proxy for {account.username}: {e}")
            return None
    
    def _is_proxy_blocked(self, proxy: Proxy) -> bool:
        """Check if proxy is blocked in memory cache"""
        proxy_key = f"{proxy.host}:{proxy.port}"
        return proxy_key in self.blocked_proxies
    
    def _get_available_proxies(self, account: InstagramAccount, exclude_blocked: bool = True) -> List[Proxy]:
        """Get list of available proxies"""
        try:
            # Base query for active proxies
            proxies = Proxy.objects.filter(
                is_active=True,
                status='active'
            ).exclude(
                # Exclude proxies assigned to other accounts
                assigned_account__isnull=False,
                assigned_account__username__ne=account.username
            )
            
            # Exclude blocked proxies if requested
            if exclude_blocked:
                blocked_keys = list(self.blocked_proxies.keys())
                for blocked_key in blocked_keys:
                    host, port = blocked_key.split(':')
                    proxies = proxies.exclude(host=host, port=int(port))
            
            return list(proxies)
            
        except Exception as e:
            logger.error(f"[PROXY_MANAGER] Error getting available proxies: {e}")
            return []
    
    def _select_best_proxy(self, proxies: List[Proxy], account: InstagramAccount) -> Optional[Proxy]:
        """Select the best proxy from available options"""
        if not proxies:
            return None
        
        try:
            # Prefer proxies from the same region as the account's current proxy
            if account.current_proxy and account.current_proxy.country:
                same_region_proxies = [
                    p for p in proxies 
                    if p.country == account.current_proxy.country
                ]
                if same_region_proxies:
                    proxies = same_region_proxies
            
            # Prefer proxies with lower usage count
            proxy_usage = []
            for proxy in proxies:
                usage_count = self.proxy_usage_count.get(f"{proxy.host}:{proxy.port}", 0)
                proxy_usage.append((usage_count, proxy))
            
            # Sort by usage count (ascending) and select randomly from least used
            proxy_usage.sort(key=lambda x: x[0])
            min_usage = proxy_usage[0][0]
            least_used_proxies = [p for usage, p in proxy_usage if usage == min_usage]
            
            selected = random.choice(least_used_proxies)
            
            # Update usage count
            proxy_key = f"{selected.host}:{selected.port}"
            self.proxy_usage_count[proxy_key] = self.proxy_usage_count.get(proxy_key, 0) + 1
            
            return selected
            
        except Exception as e:
            logger.error(f"[PROXY_MANAGER] Error selecting best proxy: {e}")
            return random.choice(proxies) if proxies else None
    
    def should_switch_proxy(self, account: InstagramAccount, error_type: str = None) -> bool:
        """Determine if proxy should be switched based on error type"""
        try:
            # Check if we recently switched proxies
            account_key = account.username
            last_switch = self.last_proxy_switch.get(account_key)
            
            if last_switch:
                time_since_switch = (timezone.now() - last_switch).total_seconds()
                if time_since_switch < 300:  # Don't switch more than once per 5 minutes
                    return False
            
            # Switch based on error type
            switch_errors = [
                'blocked', 'banned', 'challenge', 'captcha', '403', '429', 
                'rate_limit', 'login_required', 'jsondecode'
            ]
            
            if error_type and any(err in error_type.lower() for err in switch_errors):
                return True
            
            # Check if current proxy is blocked
            if account.current_proxy and self._is_proxy_blocked(account.current_proxy):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[PROXY_MANAGER] Error checking if should switch proxy: {e}")
            return False
    
    def switch_proxy(self, account: InstagramAccount, error_type: str = None) -> Optional[Proxy]:
        """Switch to a new proxy for the account"""
        try:
            account_key = account.username
            
            # Mark current proxy as blocked if it exists
            if account.current_proxy:
                self.mark_proxy_blocked(account.current_proxy, account, error_type or "auto_switch")
            
            # Get new proxy
            new_proxy = self.get_available_proxy(account, exclude_blocked=True)
            
            if new_proxy:
                # Update last switch time
                self.last_proxy_switch[account_key] = timezone.now()
                
                logger.info(f"[PROXY_MANAGER] Switched proxy for {account.username} to {new_proxy.host}:{new_proxy.port}")
                
                # Add delay after proxy switch
                delay = random.uniform(10.0, 30.0)
                logger.info(f"[PROXY_MANAGER] Waiting {delay:.1f}s after proxy switch...")
                time.sleep(delay)
                
                return new_proxy
            else:
                logger.error(f"[PROXY_MANAGER] No available proxies for {account.username}")
                return None
                
        except Exception as e:
            logger.error(f"[PROXY_MANAGER] Error switching proxy for {account.username}: {e}")
            return None
    
    def validate_and_cleanup_proxies(self):
        """Validate proxies and cleanup blocked ones"""
        try:
            logger.info("[PROXY_MANAGER] Starting proxy validation and cleanup...")
            
            # Get all active proxies
            active_proxies = Proxy.objects.filter(is_active=True)
            
            for proxy in active_proxies:
                try:
                    # Validate proxy
                    is_valid, message, geo_info = validate_proxy(
                        proxy.host, 
                        proxy.port, 
                        proxy.username, 
                        proxy.password,
                        timeout=10,
                        proxy_type=proxy.proxy_type
                    )
                    
                    if not is_valid:
                        logger.warning(f"[PROXY_MANAGER] Proxy {proxy.host}:{proxy.port} failed validation: {message}")
                        proxy.status = 'banned'
                        proxy.last_checked = timezone.now()
                        proxy.notes = f"Validation failed: {message}"
                        proxy.save(update_fields=['status', 'last_checked', 'notes'])
                    else:
                        # Update geo info
                        if geo_info.get('country'):
                            proxy.country = geo_info['country']
                        if geo_info.get('city'):
                            proxy.city = geo_info['city']
                        
                        proxy.status = 'active'
                        proxy.last_checked = timezone.now()
                        proxy.save(update_fields=['status', 'country', 'city', 'last_checked'])
                        
                        logger.debug(f"[PROXY_MANAGER] Proxy {proxy.host}:{proxy.port} validated successfully")
                    
                    # Add delay between validations
                    time.sleep(random.uniform(1.0, 3.0))
                    
                except Exception as e:
                    logger.error(f"[PROXY_MANAGER] Error validating proxy {proxy.host}:{proxy.port}: {e}")
                    continue
            
            logger.info("[PROXY_MANAGER] Proxy validation and cleanup completed")
            
        except Exception as e:
            logger.error(f"[PROXY_MANAGER] Error during proxy validation and cleanup: {e}")
    
    def get_proxy_stats(self) -> Dict:
        """Get proxy statistics"""
        try:
            total_proxies = Proxy.objects.count()
            active_proxies = Proxy.objects.filter(is_active=True, status='active').count()
            blocked_proxies = Proxy.objects.filter(status='banned').count()
            assigned_proxies = Proxy.objects.filter(assigned_account__isnull=False).count()
            
            return {
                'total': total_proxies,
                'active': active_proxies,
                'blocked': blocked_proxies,
                'assigned': assigned_proxies,
                'available': active_proxies - assigned_proxies,
                'blocked_in_memory': len(self.blocked_proxies)
            }
            
        except Exception as e:
            logger.error(f"[PROXY_MANAGER] Error getting proxy stats: {e}")
            return {}


# Global proxy manager instance
proxy_manager = ProxyManager()
