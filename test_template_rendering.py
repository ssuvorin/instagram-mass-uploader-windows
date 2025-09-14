#!/usr/bin/env python
"""
Тест для проверки отображения client_filter в шаблоне
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_uploader.settings')
django.setup()

from django.template import Template, Context
from uploader.forms import BulkUploadTaskForm

def test_template_rendering():
    """Тест отображения client_filter в шаблоне"""
    print("=== Тест отображения client_filter в шаблоне ===")
    
    # Создаем форму
    form = BulkUploadTaskForm()
    
    # Проверяем поле client_filter
    client_filter_field = form.fields.get('client_filter')
    if client_filter_field:
        print("✓ Поле client_filter найдено в форме")
        print(f"  Тип поля: {type(client_filter_field).__name__}")
        print(f"  Choices: {client_filter_field.choices}")
        print(f"  Widget: {type(client_filter_field.widget).__name__}")
        print(f"  Widget attrs: {client_filter_field.widget.attrs}")
        
        # Тестируем условие из шаблона
        has_choices = bool(client_filter_field.choices)
        print(f"  form.client_filter.field.choices: {has_choices}")
        
        if has_choices:
            print("✓ Поле должно отображаться в шаблоне")
        else:
            print("✗ Поле НЕ будет отображаться в шаблоне")
            
        # Рендерим поле
        try:
            rendered_field = str(form['client_filter'])
            print(f"  Rendered HTML: {rendered_field[:100]}...")
        except Exception as e:
            print(f"  Ошибка рендеринга: {e}")
    else:
        print("✗ Поле client_filter НЕ найдено в форме")

if __name__ == "__main__":
    test_template_rendering()