#!/bin/bash

# Скрипт для подготовки проекта к деплою

# Очистка временных и ненужных файлов
echo "Очистка временных файлов..."
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name ".DS_Store" -delete

# Создание директорий, которые могут потребоваться
echo "Создание необходимых директорий..."
mkdir -p static
mkdir -p media
mkdir -p staticfiles

# Удаление виртуального окружения и других тяжелых директорий
echo "Удаление тяжелых директорий..."
rm -rf venv
rm -rf node_modules
rm -rf .git

# Обновление разрешений на исполняемые файлы
echo "Обновление разрешений..."
chmod +x deploy.sh
chmod +x manage.py
chmod +x create_superuser.py

# Удаление ненужных для продакшена файлов
echo "Удаление тестовых файлов..."
rm -f test_*.py

# Создание .env файла для продакшена
echo "Создание .env файла..."
cat > .env << EOL
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_HOSTS=localhost,127.0.0.1,212.113.109.49
EOL

echo "Проект подготовлен к деплою."
echo "Теперь можно выполнить:"
echo "scp -r $(pwd) root@212.113.109.49:/root/" 