#!/usr/bin/env python3
"""
Test script for enhanced captcha solving system
"""

import asyncio
import os
import sys
import logging
from playwright.async_api import async_playwright

# Add uploader to path
sys.path.insert(0, 'uploader')

from enhanced_captcha_solver import EnhancedCaptchaSolver, CaptchaConfig
from captcha_detection import EnhancedCaptchaDetector

# Use centralized logging - all logs go to django.log
logger = logging.getLogger('scripts.test_captcha_enhancement')


async def test_captcha_detection():
    """Test captcha detection on a test page"""
    print("🧪 Testing Enhanced Captcha Detection System")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Test on Google reCAPTCHA demo page
            print("📄 Loading reCAPTCHA demo page...")
            await page.goto('https://www.google.com/recaptcha/api2/demo')
            await asyncio.sleep(3)
            
            # Test detection
            detector = EnhancedCaptchaDetector()
            captcha_params = await detector.detect_captcha_type(page)
            
            print(f"🔍 Detection Result:")
            print(f"  - Type: {captcha_params.captcha_type.value}")
            print(f"  - Site Key: {captcha_params.site_key}")
            print(f"  - Page URL: {captcha_params.page_url}")
            print(f"  - Invisible: {captcha_params.invisible}")
            
            if captcha_params.captcha_type.value != 'none':
                print("✅ Captcha detection working!")
                
                # Test solving (if API key is available)
                api_key = os.getenv('RUCAPTCHA_API_KEY')
                if api_key:
                    print("\n🤖 Testing Enhanced Captcha Solver...")
                    
                    config = CaptchaConfig(
                        rucaptcha_api_key=api_key,
                        enable_audio_challenge=True,
                        enable_api_fallback=True
                    )
                    
                    solver = EnhancedCaptchaSolver(config)
                    result = await solver.solve_captcha(page)
                    
                    print(f"🎯 Solving Result:")
                    print(f"  - Success: {result.success}")
                    print(f"  - Method: {result.method_used.value if result.method_used else 'None'}")
                    print(f"  - Time: {result.processing_time:.1f}s")
                    print(f"  - Error: {result.error_message or 'None'}")
                    
                    if result.success:
                        print("✅ Captcha solving working!")
                    else:
                        print("❌ Captcha solving failed")
                else:
                    print("⚠️ No RUCAPTCHA_API_KEY found, skipping solver test")
            else:
                print("❌ No captcha detected on demo page")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            
        finally:
            await browser.close()


async def test_youtube_integration():
    """Test integration with YouTube login flow"""
    print("\n🎬 Testing YouTube Integration")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to YouTube Studio (will redirect to login)
            print("📄 Loading YouTube Studio (login page)...")
            await page.goto('https://studio.youtube.com')
            await asyncio.sleep(5)
            
            # Check if captcha appears during login flow
            detector = EnhancedCaptchaDetector()
            captcha_params = await detector.detect_captcha_type(page)
            
            print(f"🔍 YouTube Login Captcha Check:")
            print(f"  - Type: {captcha_params.captcha_type.value}")
            print(f"  - Current URL: {page.url}")
            
            if captcha_params.captcha_type.value != 'none':
                print("🎯 Captcha detected in YouTube login flow!")
                print("  This is where our enhanced solver would activate")
            else:
                print("✅ No captcha detected in current YouTube login state")
                
        except Exception as e:
            print(f"❌ YouTube integration test failed: {e}")
            
        finally:
            await browser.close()


async def main():
    """Run all tests"""
    print("🚀 Enhanced Captcha System Test Suite")
    print("=" * 60)
    
    # Test 1: Basic captcha detection
    await test_captcha_detection()
    
    # Test 2: YouTube integration
    await test_youtube_integration()
    
    print("\n" + "=" * 60)
    print("✅ Test suite completed!")
    print("\n📋 Summary:")
    print("  - Enhanced captcha detection system implemented")
    print("  - Multi-method solver with audio + API fallback")
    print("  - Improved error handling and 400 error prevention")
    print("  - Integration with existing YouTube automation")
    
    print("\n🔧 Next Steps:")
    print("  1. Set RUCAPTCHA_API_KEY environment variable for API testing")
    print("  2. Test with real YouTube accounts in production")
    print("  3. Monitor success rates and adjust timeouts if needed")


if __name__ == "__main__":
    asyncio.run(main())