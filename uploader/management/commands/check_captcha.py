import os
from django.core.management.base import BaseCommand
from django.conf import settings
from uploader.captcha_solver import RuCaptchaSolver

class Command(BaseCommand):
    help = 'Check reCAPTCHA solver configuration and balance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-key',
            type=str,
            help='Test with a specific API key',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🤖 reCAPTCHA Solver Configuration Check')
        )
        self.stdout.write("=" * 50)
        
        # Check API key configuration
        api_key = options.get('test_key')
        if not api_key:
            api_key = (
                os.environ.get('RUCAPTCHA_API_KEY') or 
                os.environ.get('CAPTCHA_API_KEY') or
                getattr(settings, 'RUCAPTCHA_API_KEY', '') or
                getattr(settings, 'CAPTCHA_API_KEY', '')
            )
        
        if not api_key:
            self.stdout.write(
                self.style.ERROR('❌ No API key found!')
            )
            self.stdout.write(
                "Please set one of the following environment variables:"
            )
            self.stdout.write("  - RUCAPTCHA_API_KEY")
            self.stdout.write("  - CAPTCHA_API_KEY")
            self.stdout.write("")
            self.stdout.write("Or get your API key from:")
            self.stdout.write("  🔗 https://rucaptcha.com")
            return
        
        # Mask API key for display
        masked_key = api_key[:8] + "*" * (len(api_key) - 12) + api_key[-4:] if len(api_key) > 12 else "****"
        self.stdout.write(f"✅ API Key: {masked_key}")
        
        # Test the solver
        self.stdout.write("\n🔍 Testing connection to ruCAPTCHA...")
        solver = RuCaptchaSolver(api_key)
        
        try:
            balance = solver.get_balance()
            
            if balance is not None:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Connection successful!')
                )
                self.stdout.write(f"💰 Account balance: ${balance}")
                
                if balance < 1.0:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Low balance: ${balance}')
                    )
                    self.stdout.write("Consider topping up your account for automatic captcha solving.")
                elif balance < 5.0:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Balance getting low: ${balance}')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Good balance: ${balance}')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Failed to get balance - check your API key')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error testing connection: {str(e)}')
            )
        
        # Configuration tips
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("💡 Configuration Tips:")
        self.stdout.write("")
        
        self.stdout.write("1. Set your API key as environment variable:")
        self.stdout.write("   export RUCAPTCHA_API_KEY='your_api_key_here'")
        self.stdout.write("")
        
        self.stdout.write("2. Or add to your .env file:")
        self.stdout.write("   RUCAPTCHA_API_KEY=your_api_key_here")
        self.stdout.write("")
        
        self.stdout.write("3. reCAPTCHA solving costs:")
        self.stdout.write("   - reCAPTCHA v2: ~$1 per 1000 solutions")
        self.stdout.write("   - Solving time: 10-120 seconds")
        self.stdout.write("")
        
        self.stdout.write("4. Get API key and top up balance at:")
        self.stdout.write("   🔗 https://rucaptcha.com")
        
        if options.get('verbose'):
            self.stdout.write("\n🔧 Environment Variables:")
            env_vars = [
                'RUCAPTCHA_API_KEY',
                'CAPTCHA_API_KEY', 
                'DOLPHIN_API_TOKEN'
            ]
            
            for var in env_vars:
                value = os.environ.get(var, 'Not set')
                if value != 'Not set' and len(value) > 8:
                    value = value[:4] + "*" * (len(value) - 8) + value[-4:]
                self.stdout.write(f"  {var}: {value}")
        
        self.stdout.write("\n✅ Configuration check complete!") 