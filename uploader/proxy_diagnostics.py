#!/usr/bin/env python
"""
Диагностика прокси для Dolphin Anty профилей
Проверяет подключение к прокси перед использованием
"""

import os
import sys
import django
import requests
import socket
import time
from typing import Dict, Tuple, Optional

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from uploader.models import InstagramAccount, Proxy
from uploader.utils import validate_proxy

def diagnose_account_proxy(account_id: int) -> Dict:
    """Диагностика прокси для конкретного аккаунта"""
    try:
        account = InstagramAccount.objects.get(id=account_id)
        
        result = {
            'account_id': account_id,
            'username': account.username,
            'dolphin_profile_id': account.dolphin_profile_id,
            'proxy_assigned': bool(account.proxy),
            'proxy_details': None,
            'proxy_test': None,
            'recommendations': []
        }
        
        if not account.proxy:
            result['recommendations'].append("[FAIL] No proxy assigned to account")
            return result
        
        proxy = account.proxy
        result['proxy_details'] = {
            'host': proxy.host,
            'port': proxy.port,
            'type': proxy.proxy_type,
            'country': proxy.country,
            'status': proxy.status,
            'is_active': proxy.is_active,
            'last_verified': proxy.last_verified.isoformat() if proxy.last_verified else None
        }
        
        # Тестируем прокси
        print(f"🔍 Testing proxy for account {account.username}...")
        is_valid, message, geo_info = validate_proxy(
            host=proxy.host,
            port=proxy.port,
            username=proxy.username,
            password=proxy.password,
            timeout=15,
            proxy_type=proxy.proxy_type
        )
        
        result['proxy_test'] = {
            'is_valid': is_valid,
            'message': message,
            'geo_info': geo_info,
            'test_time': time.time()
        }
        
        # Рекомендации
        if not is_valid:
            result['recommendations'].append(f"[FAIL] Proxy test failed: {message}")
            result['recommendations'].append("[TOOL] Try changing to a different proxy")
        else:
            result['recommendations'].append("[OK] Proxy is working correctly")
            
        if proxy.status != 'active':
            result['recommendations'].append(f"[WARN] Proxy status is '{proxy.status}', should be 'active'")
            
        if not proxy.is_active:
            result['recommendations'].append("[WARN] Proxy is marked as inactive")
            
        return result
        
    except InstagramAccount.DoesNotExist:
        return {
            'account_id': account_id,
            'error': f'Account with ID {account_id} not found'
        }
    except Exception as e:
        return {
            'account_id': account_id,
            'error': f'Error diagnosing account: {str(e)}'
        }

def diagnose_dolphin_profile_proxy(profile_id: str) -> Dict:
    """Диагностика прокси для Dolphin профиля"""
    try:
        # Найти аккаунт с этим профилем
        account = InstagramAccount.objects.get(dolphin_profile_id=profile_id)
        return diagnose_account_proxy(account.id)
    except InstagramAccount.DoesNotExist:
        return {
            'profile_id': profile_id,
            'error': f'No account found with Dolphin profile ID {profile_id}'
        }

def diagnose_all_accounts_with_dolphin_profiles() -> Dict:
    """Диагностика всех аккаунтов с Dolphin профилями"""
    accounts = InstagramAccount.objects.filter(dolphin_profile_id__isnull=False)
    
    results = {
        'total_accounts': accounts.count(),
        'accounts': [],
        'summary': {
            'with_proxy': 0,
            'without_proxy': 0,
            'proxy_working': 0,
            'proxy_failing': 0
        }
    }
    
    for account in accounts:
        print(f"Diagnosing account {account.username} (ID: {account.id})...")
        result = diagnose_account_proxy(account.id)
        results['accounts'].append(result)
        
        if result.get('proxy_assigned'):
            results['summary']['with_proxy'] += 1
            if result.get('proxy_test', {}).get('is_valid'):
                results['summary']['proxy_working'] += 1
            else:
                results['summary']['proxy_failing'] += 1
        else:
            results['summary']['without_proxy'] += 1
    
    return results

def test_proxy_connectivity(host: str, port: int, timeout: int = 10) -> Tuple[bool, str]:
    """Простая проверка TCP подключения к прокси"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return True, "TCP connection successful"
        else:
            return False, f"TCP connection failed (error code: {result})"
    except socket.gaierror as e:
        return False, f"DNS resolution failed: {str(e)}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def fix_account_proxy_issues(account_id: int, auto_fix: bool = False) -> Dict:
    """Попытка исправить проблемы с прокси аккаунта"""
    try:
        account = InstagramAccount.objects.get(id=account_id)
        
        result = {
            'account_id': account_id,
            'username': account.username,
            'fixes_applied': [],
            'success': False
        }
        
        if not account.proxy:
            if auto_fix:
                # Попытка назначить доступный прокси
                available_proxy = Proxy.objects.filter(
                    is_active=True,
                    assigned_account__isnull=True
                ).first()
                
                if available_proxy:
                    account.proxy = available_proxy
                    account.current_proxy = available_proxy
                    available_proxy.assigned_account = account
                    account.save(update_fields=['proxy', 'current_proxy'])
                    available_proxy.save(update_fields=['assigned_account'])
                    result['fixes_applied'].append(f"[OK] Assigned proxy {available_proxy.host}:{available_proxy.port}")
                else:
                    result['fixes_applied'].append("[FAIL] No available proxies to assign")
            else:
                result['fixes_applied'].append("[WARN] No proxy assigned (use --auto-fix to assign)")
            
            return result
        
        # Проверяем текущий прокси
        proxy = account.proxy
        is_valid, message, _ = validate_proxy(
            host=proxy.host,
            port=proxy.port,
            username=proxy.username,
            password=proxy.password,
            timeout=10,
            proxy_type=proxy.proxy_type
        )
        
        if not is_valid:
            result['fixes_applied'].append(f"[FAIL] Current proxy is not working: {message}")
            
            if auto_fix:
                # Попытка найти другой рабочий прокси
                alternative_proxies = Proxy.objects.filter(
                    is_active=True,
                    assigned_account__isnull=True
                )
                
                for alt_proxy in alternative_proxies[:3]:  # Проверяем до 3 альтернатив
                    alt_valid, alt_message, _ = validate_proxy(
                        host=alt_proxy.host,
                        port=alt_proxy.port,
                        username=alt_proxy.username,
                        password=alt_proxy.password,
                        timeout=10,
                        proxy_type=alt_proxy.proxy_type
                    )
                    
                    if alt_valid:
                        # Освобождаем старый прокси
                        proxy.assigned_account = None
                        proxy.save(update_fields=['assigned_account'])
                        
                        # Назначаем новый - обновляем оба поля
                        account.proxy = alt_proxy
                        account.current_proxy = alt_proxy
                        alt_proxy.assigned_account = account
                        account.save(update_fields=['proxy', 'current_proxy'])
                        alt_proxy.save(update_fields=['assigned_account'])
                        
                        result['fixes_applied'].append(f"[OK] Switched to working proxy {alt_proxy.host}:{alt_proxy.port}")
                        result['success'] = True
                        break
                else:
                    result['fixes_applied'].append("[FAIL] No working alternative proxies found")
            else:
                result['fixes_applied'].append("[WARN] Proxy not working (use --auto-fix to find alternative)")
        else:
            result['fixes_applied'].append("[OK] Current proxy is working correctly")
            result['success'] = True
        
        return result
        
    except Exception as e:
        return {
            'account_id': account_id,
            'error': f'Error fixing account proxy: {str(e)}'
        }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnose proxy issues for Dolphin Anty accounts")
    parser.add_argument('--account-id', type=int, help='Diagnose specific account by ID')
    parser.add_argument('--profile-id', type=str, help='Diagnose specific Dolphin profile by ID')
    parser.add_argument('--all', action='store_true', help='Diagnose all accounts with Dolphin profiles')
    parser.add_argument('--fix', type=int, metavar='ACCOUNT_ID', help='Try to fix proxy issues for account')
    parser.add_argument('--auto-fix', action='store_true', help='Automatically apply fixes when using --fix')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    
    args = parser.parse_args()
    
    if not any([args.account_id, args.profile_id, args.all, args.fix]):
        parser.print_help()
        return
    
    if args.fix:
        print(f"[TOOL] Attempting to fix proxy issues for account {args.fix}...")
        result = fix_account_proxy_issues(args.fix, auto_fix=args.auto_fix)
        
        if args.json:
            import json
            print(json.dumps(result, indent=2))
        else:
            print(f"\nAccount: {result.get('username', 'Unknown')} (ID: {result['account_id']})")
            for fix in result.get('fixes_applied', []):
                print(f"  {fix}")
            
            if result.get('success'):
                print("\n[OK] Proxy issues resolved!")
            elif result.get('error'):
                print(f"\n[FAIL] Error: {result['error']}")
            else:
                print("\n[WARN] Some issues remain unresolved")
        
        return
    
    if args.account_id:
        print(f"🔍 Diagnosing proxy for account {args.account_id}...")
        result = diagnose_account_proxy(args.account_id)
    elif args.profile_id:
        print(f"🔍 Diagnosing proxy for Dolphin profile {args.profile_id}...")
        result = diagnose_dolphin_profile_proxy(args.profile_id)
    elif args.all:
        print("🔍 Diagnosing proxies for all accounts with Dolphin profiles...")
        result = diagnose_all_accounts_with_dolphin_profiles()
    
    if args.json:
        import json
        print(json.dumps(result, indent=2, default=str))
    else:
        # Pretty print results
        if args.all:
            print(f"\n📊 Summary:")
            print(f"  Total accounts: {result['total_accounts']}")
            print(f"  With proxy: {result['summary']['with_proxy']}")
            print(f"  Without proxy: {result['summary']['without_proxy']}")
            print(f"  Proxy working: {result['summary']['proxy_working']}")
            print(f"  Proxy failing: {result['summary']['proxy_failing']}")
            
            print(f"\n📋 Account Details:")
            for acc in result['accounts']:
                if acc.get('error'):
                    print(f"  [FAIL] {acc['username']} (ID: {acc['account_id']}): {acc['error']}")
                else:
                    status = "[OK]" if acc.get('proxy_test', {}).get('is_valid') else "[FAIL]"
                    print(f"  {status} {acc['username']} (ID: {acc['account_id']}) - Profile: {acc['dolphin_profile_id']}")
                    
                    if acc.get('recommendations'):
                        for rec in acc['recommendations']:
                            print(f"    {rec}")
        else:
            if result.get('error'):
                print(f"[FAIL] Error: {result['error']}")
            else:
                print(f"\n📋 Account: {result['username']} (ID: {result['account_id']})")
                print(f"🐬 Dolphin Profile: {result['dolphin_profile_id']}")
                
                if result['proxy_assigned']:
                    proxy = result['proxy_details']
                    print(f"🌐 Proxy: {proxy['host']}:{proxy['port']} ({proxy['type']}) - {proxy['country']}")
                    print(f"📊 Status: {proxy['status']} (Active: {proxy['is_active']})")
                    
                    test = result.get('proxy_test', {})
                    if test.get('is_valid'):
                        print(f"[OK] Proxy Test: PASSED - {test['message']}")
                    else:
                        print(f"[FAIL] Proxy Test: FAILED - {test['message']}")
                else:
                    print("[FAIL] No proxy assigned")
                
                print(f"\n💡 Recommendations:")
                for rec in result.get('recommendations', []):
                    print(f"  {rec}")

if __name__ == "__main__":
    main() 