#!/usr/bin/env python
"""
Test script for analytics collector to debug 500 error
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from cabinet.models import Client as CabinetClient
from uploader.models import HashtagAnalytics

def test_analytics_collector():
    """Test analytics collector functionality"""
    print("Testing Analytics Collector...")
    
    # Create test client
    client = Client()
    
    # Get superuser
    try:
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ No superuser found")
            return False
        
        print(f"✅ Found superuser: {user.username}")
        
        # Login
        client.force_login(user)
        
        # Get a cabinet client
        cabinet_client = CabinetClient.objects.first()
        if not cabinet_client:
            print("❌ No cabinet clients found")
            return False
        
        print(f"✅ Found cabinet client: {cabinet_client.name}")
        
        # Test GET request
        print("\n🔍 Testing GET request...")
        response = client.get('/analytics/collector/')
        print(f"GET response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ GET request failed: {response.status_code}")
            return False
        
        # Test POST request
        print("\n🔍 Testing POST request...")
        response = client.post('/analytics/collector/', {
            'client_id': str(cabinet_client.id),
            'social_network': 'INSTAGRAM',
            'hashtag': 'test',
            'analyzed_medias': '10',
            'total_views': '1000',
            'created_at': '2025-01-08T12:00:00'
        })
        
        print(f"POST response status: {response.status_code}")
        
        if response.status_code == 302:
            print("✅ POST request successful (redirect)")
            return True
        elif response.status_code == 200:
            print("⚠️ POST request returned 200 (form errors)")
            # Check for form errors
            if hasattr(response, 'context') and 'form' in response.context:
                form = response.context['form']
                if form.errors:
                    print("Form errors:")
                    for field, errors in form.errors.items():
                        print(f"  {field}: {errors}")
            return False
        else:
            print(f"❌ POST request failed: {response.status_code}")
            if hasattr(response, 'content'):
                print(f"Response content: {response.content.decode()[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_model_creation():
    """Test HashtagAnalytics model creation"""
    print("\n🔍 Testing HashtagAnalytics model...")
    
    try:
        # Test creating a HashtagAnalytics record
        user = User.objects.filter(is_superuser=True).first()
        cabinet_client = CabinetClient.objects.first()
        
        if not user or not cabinet_client:
            print("❌ Missing user or client")
            return False
        
        analytics = HashtagAnalytics.objects.create(
            hashtag='test',
            client=cabinet_client,
            social_network='INSTAGRAM',
            is_manual=True,
            created_by=user,
            analyzed_medias=10,
            total_views=1000
        )
        
        print(f"✅ Created HashtagAnalytics record: {analytics.id}")
        
        # Clean up
        analytics.delete()
        print("✅ Cleaned up test record")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating model: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("Analytics Collector Debug Test")
    print("=" * 50)
    
    # Test model creation first
    model_ok = test_model_creation()
    
    # Test analytics collector
    collector_ok = test_analytics_collector()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Model creation: {'✅ PASS' if model_ok else '❌ FAIL'}")
    print(f"Analytics collector: {'✅ PASS' if collector_ok else '❌ FAIL'}")
    print("=" * 50)
