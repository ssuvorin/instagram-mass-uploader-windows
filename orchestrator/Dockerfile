FROM python:3.11-slim

# Метаданные образа
LABEL maintainer="TikTok Bot Orchestrator Team"
LABEL description="Система оркестровки для управления серверами TikTok ботов"
LABEL version="1.0.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для безопасности
RUN groupadd -r orchestrator && useradd -r -g orchestrator orchestrator

# Установка рабочей директории
WORKDIR /app

# Копирование requirements и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p /app/data /app/logs && \
    chown -R orchestrator:orchestrator /app

# Переключение на непривилегированного пользователя
USER orchestrator

# Переменные окружения
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:///data/orchestrator.db
ENV API_PORT=9000
ENV LOG_LEVEL=INFO

# Проверка здоровья контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Открытие порта
EXPOSE 9000

# Команда запуска
CMD ["python", "main.py"]
