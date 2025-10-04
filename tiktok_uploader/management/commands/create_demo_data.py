from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tiktok_uploader.models import TikTokAccount, TikTokProxy, BulkUploadTask


class Command(BaseCommand):
    help = 'Создает демонстрационные данные для TikTok Uploader'

    def handle(self, *args, **options):
        self.stdout.write('Создание демонстрационных данных...')
        
        # Создаем тестового пользователя если его нет
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
            self.stdout.write(f'Создан пользователь: {user.username}')
        
        # Создаем несколько тестовых аккаунтов TikTok
        accounts_data = [
            {'username': '@demo_account1', 'email': 'demo1@example.com'},
            {'username': '@demo_account2', 'email': 'demo2@example.com'},
            {'username': '@demo_account3', 'email': 'demo3@example.com'},
        ]
        
        for account_data in accounts_data:
            account, created = TikTokAccount.objects.get_or_create(
                username=account_data['username'],
                defaults={
                    'email': account_data['email'],
                    'status': 'ACTIVE',
                }
            )
            if created:
                self.stdout.write(f'Создан аккаунт: {account.username}')
        
        # Создаем несколько тестовых прокси
        proxies_data = [
            {'ip': '192.168.1.100', 'port': 8080},
            {'ip': '192.168.1.101', 'port': 8080},
        ]
        
        for proxy_data in proxies_data:
            proxy, created = TikTokProxy.objects.get_or_create(
                ip=proxy_data['ip'],
                port=proxy_data['port'],
                defaults={
                    'status': 'active',
                    'proxy_type': 'HTTP',
                }
            )
            if created:
                self.stdout.write(f'Создан прокси: {proxy.ip}:{proxy.port}')
        
        # Создаем несколько тестовых задач
        tasks_data = [
            {
                'name': 'Демо загрузка #1',
                'status': 'PENDING',
            },
            {
                'name': 'Демо загрузка #2', 
                'status': 'COMPLETED',
            },
        ]
        
        for task_data in tasks_data:
            task, created = BulkUploadTask.objects.get_or_create(
                name=task_data['name'],
                defaults={
                    'status': task_data['status'],
                    'created_by': user,
                }
            )
            if created:
                self.stdout.write(f'Создана задача: {task.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Демонстрационные данные успешно созданы!')
        )

