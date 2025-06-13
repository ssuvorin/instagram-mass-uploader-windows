#!/bin/bash

# Make sure script exits on any error
set -e

echo "Starting deployment process..."

# Build the Docker images
echo "Building Docker images..."
docker-compose build

# Start the containers in detached mode
echo "Starting containers..."
docker-compose up -d

# Apply migrations
echo "Applying migrations..."
docker-compose exec web python manage.py migrate

echo "Deployment completed successfully!"
echo "Your application should be running at http://localhost:8000"
echo "Note: For production, make sure to update the SECRET_KEY and ALLOWED_HOSTS in docker-compose.yml" 