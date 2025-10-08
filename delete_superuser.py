#!/usr/bin/env python
"""
Скрипт для удаления суперпользователя Django
Использование: python delete_superuser.py brazino
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from django.contrib.auth import get_user_model

def delete_superuser(username):
    User = get_user_model()
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"❌ Пользователь с именем '{username}' не найден")
        return False
    
    # Проверяем, что это действительно суперпользователь
    if not user.is_superuser:
        print(f"❌ Пользователь '{username}' не является суперпользователем")
        return False
    
    print(f"🔍 Найден суперпользователь: {user.username}")
    print(f"   ID: {user.id}")
    print(f"   Email: {user.email}")
    print(f"   Дата регистрации: {user.date_joined}")
    print(f"   Последний вход: {user.last_login}")
    
    # Запрашиваем подтверждение
    confirmation = input(f"\n⚠️  Вы уверены, что хотите удалить суперпользователя '{username}'? (y/N): ").lower()
    if confirmation != 'y':
        print("❌ Удаление отменено")
        return False
    
    # Удаляем пользователя
    user.delete()
    print(f"✅ Суперпользователь '{username}' успешно удален")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Использование: python delete_superuser.py <username>")
        print("Пример: python delete_superuser.py brazino")
        sys.exit(1)
    
    username = sys.argv[1]
    success = delete_superuser(username)
    sys.exit(0 if success else 1)
