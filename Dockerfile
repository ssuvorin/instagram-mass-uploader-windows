FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libjpeg-dev \
    libpq-dev \
    libssl-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and browsers
RUN pip install --no-cache-dir playwright
RUN playwright install chromium
RUN playwright install-deps

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create static directory if it doesn't exist
RUN mkdir -p /app/static

# Collect static files
RUN python manage.py collectstatic --noinput --clear

# Run gunicorn with WhiteNoise for static files
CMD ["gunicorn", "wsgi_static:application", "--bind", "0.0.0.0:8000"] 