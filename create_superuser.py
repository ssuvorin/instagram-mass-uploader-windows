#!/usr/bin/env python
"""
Автоматическое создание суперпользователя Django
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_superuser():
    User = get_user_model()
    
    # Проверяем существует ли уже суперпользователь
    if User.objects.filter(is_superuser=True).exists():
        print("🔐 Superuser already exists, skipping creation")
        return
    
    # Создаем суперпользователя
    try:
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        print("✅ Superuser created successfully:")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Email: admin@example.com")
        print("⚠️  ВАЖНО: Смените пароль после первого входа!")
    except Exception as e:
        print(f"❌ Error creating superuser: {e}")
        sys.exit(1)

if __name__ == '__main__':
    create_superuser() 