#!/bin/bash
# =============================================================================
# СБОРКА DOCKER ОБРАЗА НА MAC ДЛЯ WINDOWS СЕРВЕРА
# =============================================================================

set -e

echo "🚀 Starting cross-platform Docker build for Windows deployment..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверяем что мы на Mac
if [[ "$OSTYPE" != "darwin"* ]]; then
    log_warning "This script is optimized for macOS. Current OS: $OSTYPE"
fi

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

log_info "Docker version: $(docker --version)"

# Проверяем Docker Buildx (для мультиплатформенной сборки)
if ! docker buildx version &> /dev/null; then
    log_error "Docker Buildx is required for cross-platform builds"
    log_info "Please enable Docker Buildx in Docker Desktop settings"
    exit 1
fi

log_success "Docker Buildx is available"

# Создаем builder instance для мультиплатформенной сборки
BUILDER_NAME="instagram-uploader-builder"

log_info "Setting up cross-platform builder..."
if ! docker buildx ls | grep -q "$BUILDER_NAME"; then
    docker buildx create --name "$BUILDER_NAME" --driver docker-container --bootstrap
    log_success "Created new builder: $BUILDER_NAME"
else
    log_info "Builder $BUILDER_NAME already exists"
fi

# Используем наш builder
docker buildx use "$BUILDER_NAME"

# Определяем платформы
PLATFORMS="linux/amd64"  # Windows Docker обычно использует AMD64
log_info "Target platform: $PLATFORMS"

# Определяем теги
IMAGE_NAME="instagram-uploader"
VERSION="latest"
WINDOWS_TAG="$IMAGE_NAME:windows-$VERSION"

log_info "Building image: $WINDOWS_TAG"
log_info "Target platform: $PLATFORMS"

# Сборка для Windows (AMD64)
log_info "🔨 Building Windows-compatible image..."
docker buildx build \
    --platform "$PLATFORMS" \
    --file Dockerfile.windows \
    --tag "$WINDOWS_TAG" \
    --load \
    .

if [ $? -eq 0 ]; then
    log_success "✅ Image built successfully: $WINDOWS_TAG"
else
    log_error "❌ Failed to build image"
    exit 1
fi

# Проверяем размер образа
IMAGE_SIZE=$(docker images "$WINDOWS_TAG" --format "table {{.Size}}" | tail -n 1)
log_info "📦 Image size: $IMAGE_SIZE"

# Тестируем образ (базовая проверка)
log_info "🧪 Testing image..."
if docker run --rm --platform linux/amd64 "$WINDOWS_TAG" python --version; then
    log_success "✅ Image test passed - Python is working"
else
    log_error "❌ Image test failed"
    exit 1
fi

# Проверяем Playwright
log_info "🎭 Testing Playwright installation..."
if docker run --rm --platform linux/amd64 "$WINDOWS_TAG" python -c "import playwright; print('Playwright version:', playwright.__version__)"; then
    log_success "✅ Playwright test passed"
else
    log_warning "⚠️ Playwright test failed - this might be okay if dependencies are missing"
fi

# Показываем информацию об образе
log_info "📋 Image information:"
docker inspect "$WINDOWS_TAG" --format='{{.Architecture}}' | while read arch; do
    log_info "  Architecture: $arch"
done

# Опционально: экспорт образа в tar файл для переноса
read -p "💾 Export image to tar file for manual transfer? (y/N): " export_choice
if [[ $export_choice =~ ^[Yy]$ ]]; then
    TAR_FILE="instagram-uploader-windows.tar"
    log_info "📦 Exporting image to $TAR_FILE..."
    docker save "$WINDOWS_TAG" -o "$TAR_FILE"
    log_success "✅ Image exported to $TAR_FILE"
    log_info "📋 Transfer instructions:"
    log_info "  1. Copy $TAR_FILE to your Windows server"
    log_info "  2. Run: docker load -i $TAR_FILE"
    log_info "  3. Run: docker tag $WINDOWS_TAG $IMAGE_NAME:latest"
fi

# Опционально: отправка в Docker Registry
read -p "🚀 Push to Docker Registry? (y/N): " push_choice
if [[ $push_choice =~ ^[Yy]$ ]]; then
    read -p "Enter Docker Registry URL (or press Enter for Docker Hub): " registry_url
    
    if [ -n "$registry_url" ]; then
        FULL_TAG="$registry_url/$WINDOWS_TAG"
    else
        read -p "Enter Docker Hub username: " docker_username
        FULL_TAG="$docker_username/$WINDOWS_TAG"
    fi
    
    log_info "🏷️ Tagging image as: $FULL_TAG"
    docker tag "$WINDOWS_TAG" "$FULL_TAG"
    
    log_info "🚀 Pushing to registry..."
    docker push "$FULL_TAG"
    
    if [ $? -eq 0 ]; then
        log_success "✅ Image pushed successfully: $FULL_TAG"
        log_info "📋 Windows deployment command:"
        log_info "  docker pull $FULL_TAG"
        log_info "  docker tag $FULL_TAG $IMAGE_NAME:latest"
    else
        log_error "❌ Failed to push image"
    fi
fi

log_success "🎉 Cross-platform build completed successfully!"
log_info "📋 Next steps:"
log_info "  1. Test locally: docker run -p 8000:8000 $WINDOWS_TAG"
log_info "  2. Deploy to Windows server using docker-compose.windows.yml"
log_info "  3. Make sure DOLPHIN_API_HOST=http://host.docker.internal:3001 in .env"

echo ""
log_warning "⚠️ Important notes for Windows deployment:"
log_info "  • Use docker-compose.windows.yml on Windows server"
log_info "  • Set DOLPHIN_API_HOST=http://host.docker.internal:3001"
log_info "  • Ensure Dolphin Anty is running on Windows host"
log_info "  • Check Windows firewall settings for port 3001" 