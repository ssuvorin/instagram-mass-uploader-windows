#!/usr/bin/env python3
"""
Test script for TikTok integration

This script tests the TikTok integration module and API endpoints.
Run it from the project root directory.
"""

import os
import sys
import django
import requests
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uploader.settings')
django.setup()

from uploader.tiktok_integration import (
    get_tiktok_integration,
    get_tiktok_file_manager,
    get_tiktok_config_manager
)


def test_tiktok_integration():
    """Test TikTok integration module"""
    print("Testing TikTok Integration Module...")
    
    try:
        # Test TikTok Integration
        tiktok = get_tiktok_integration()
        print(f"✓ TikTok Integration initialized with API base: {tiktok.api_base}")
        
        # Test connection
        connected = tiktok.check_connection()
        print(f"✓ API Connection: {'Connected' if connected else 'Disconnected'}")
        
        # Test File Manager
        file_manager = get_tiktok_file_manager()
        print(f"✓ File Manager initialized")
        print(f"  - Videos: {len(file_manager.list_videos())}")
        print(f"  - Titles: {len(file_manager.list_titles())}")
        print(f"  - Accounts: {len(file_manager.list_accounts())}")
        print(f"  - Proxies: {len(file_manager.list_proxies())}")
        
        # Test Config Manager
        config_manager = get_tiktok_config_manager()
        print(f"✓ Config Manager initialized")
        
        default_config = config_manager.get_default_config()
        print(f"  - Default config loaded: {len(default_config)} fields")
        
        # Test configuration validation
        test_config = {
            'upload_cycles': 5,
            'videos_per_account': 1,
            'mentions': ['user1', 'user2']
        }
        errors = config_manager.validate_config(test_config)
        if errors:
            print(f"  - Config validation errors: {errors}")
        else:
            print(f"  - Config validation: ✓ Passed")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing TikTok integration: {e}")
        return False


def test_api_endpoints():
    """Test TikTok API endpoints"""
    print("\nTesting TikTok API Endpoints...")
    
    base_url = "http://localhost:8000"
    
    try:
        # Test status endpoint
        response = requests.get(f"{base_url}/api/tiktok/status/")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status endpoint: {data.get('api_connected', 'Unknown')}")
        else:
            print(f"✗ Status endpoint failed: {response.status_code}")
        
        # Test logs endpoint
        response = requests.get(f"{base_url}/api/tiktok/logs/")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Logs endpoint: {len(data.get('logs', []))} logs")
        else:
            print(f"✗ Logs endpoint failed: {response.status_code}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to Django server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"✗ Error testing API endpoints: {e}")
        return False


def test_file_operations():
    """Test file operations"""
    print("\nTesting File Operations...")
    
    try:
        file_manager = get_tiktok_file_manager()
        
        # Test creating test files
        test_content = b"Test content for testing purposes"
        
        # Test video file
        from django.core.files.base import ContentFile
        test_video = ContentFile(test_content, name="test_video.mp4")
        filename = file_manager.save_video(test_video, "test_video.mp4")
        print(f"✓ Video file saved: {filename}")
        
        # Test titles file
        test_titles = ContentFile(b"Test title 1\nTest title 2", name="test_titles.txt")
        filename = file_manager.save_titles(test_titles, "test_titles.txt")
        print(f"✓ Titles file saved: {filename}")
        
        # Test accounts file
        test_accounts = ContentFile(b"user1:pass1:email1:emailpass1\nuser2:pass2:email2:emailpass2", name="test_accounts.txt")
        filename = file_manager.save_accounts(test_accounts, "test_accounts.txt")
        print(f"✓ Accounts file saved: {filename}")
        
        # Test proxies file
        test_proxies = ContentFile(b"host1:8080@user1:pass1\nhost2:8080@user2:pass2", name="test_proxies.txt")
        filename = file_manager.save_proxies(test_proxies, "test_proxies.txt")
        print(f"✓ Proxies file saved: {filename}")
        
        # List all files
        print(f"  - Videos: {file_manager.list_videos()}")
        print(f"  - Titles: {file_manager.list_titles()}")
        print(f"  - Accounts: {file_manager.list_accounts()}")
        print(f"  - Proxies: {file_manager.list_proxies()}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing file operations: {e}")
        return False


def main():
    """Main test function"""
    print("TikTok Integration Test Suite")
    print("=" * 40)
    
    tests = [
        ("TikTok Integration Module", test_tiktok_integration),
        ("API Endpoints", test_api_endpoints),
        ("File Operations", test_file_operations),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("Test Summary:")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! TikTok integration is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
