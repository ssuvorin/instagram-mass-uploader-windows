#!/bin/bash

# Скрипт для настройки сервера Ubuntu и запуска приложения

# Обновление системы
echo "Обновление системы..."
apt update && apt upgrade -y

# Установка необходимых пакетов
echo "Установка необходимых пакетов..."
apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx

# Запуск и автозапуск Docker
echo "Настройка Docker..."
systemctl start docker
systemctl enable docker

# Создание Nginx конфигурации
echo "Настройка Nginx..."
cat > /etc/nginx/sites-available/instagram_uploader << EOL
server {
    listen 80;
    server_name 212.113.109.49;

    location /static/ {
        alias /root/playwright_instagram_uploader/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /root/playwright_instagram_uploader/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Активация Nginx конфигурации
ln -sf /etc/nginx/sites-available/instagram_uploader /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Запуск приложения
echo "Запуск приложения..."
cd /root/playwright_instagram_uploader
docker-compose -f docker-compose.prod.yml up -d

echo "Настройка завершена!"
echo "Приложение доступно по адресу: http://212.113.109.49"
echo ""
echo "Для создания суперпользователя выполните:"
echo "docker-compose -f docker-compose.prod.yml exec web python create_superuser.py admin admin@example.com ВАШ_ПАРОЛЬ" 