#!/usr/bin/env python
"""
Скрипт для прямого удаления суперпользователя через SQL
Обходит проблемы с Django ORM и внешними ключами
Использование: python delete_superuser_sql.py brazino
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from django.db import connection

def delete_superuser_sql(username):
    """Удаляет суперпользователя напрямую через SQL"""
    
    with connection.cursor() as cursor:
        # Проверяем существование пользователя
        cursor.execute("SELECT id, username, email, is_superuser FROM auth_user WHERE username = %s", [username])
        user_data = cursor.fetchone()
        
        if not user_data:
            print(f"❌ Пользователь с именем '{username}' не найден")
            return False
        
        user_id, username_found, email, is_superuser = user_data
        
        if not is_superuser:
            print(f"❌ Пользователь '{username}' не является суперпользователем")
            return False
        
        print(f"🔍 Найден суперпользователь: {username_found}")
        print(f"   ID: {user_id}")
        print(f"   Email: {email}")
        
        # Запрашиваем подтверждение
        confirmation = input(f"\n⚠️  Вы уверены, что хотите удалить суперпользователя '{username}'? (y/N): ").lower()
        if confirmation != 'y':
            print("❌ Удаление отменено")
            return False
        
        try:
            # Удаляем пользователя напрямую через SQL
            cursor.execute("DELETE FROM auth_user WHERE username = %s", [username])
            
            if cursor.rowcount > 0:
                print(f"✅ Суперпользователь '{username}' успешно удален")
                return True
            else:
                print(f"❌ Не удалось удалить пользователя '{username}'")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при удалении: {e}")
            return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Использование: python delete_superuser_sql.py <username>")
        print("Пример: python delete_superuser_sql.py brazino")
        sys.exit(1)
    
    username = sys.argv[1]
    success = delete_superuser_sql(username)
    sys.exit(0 if success else 1)
