#!/bin/bash

# Simple Page Counter - Raspberry Pi Deployment Script

echo "🍓 Deploying Simple Page Counter to Raspberry Pi..."
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    print_warning "Please log out and log back in for Docker permissions to take effect"
    exit 1
fi
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p data config ssl

# Set proper permissions for data directory
sudo chown -R 1000:1000 data

# Check Raspberry Pi architecture
ARCH=$(uname -m)
print_status "Detected architecture: $ARCH"

if [[ "$ARCH" == "armv7l" || "$ARCH" == "aarch64" ]]; then
    print_status "Raspberry Pi detected. Optimizing for ARM architecture..."
else
    print_warning "Non-ARM architecture detected. This script is optimized for Raspberry Pi."
fi

# Build and start the containers
print_status "Building Docker image..."
docker-compose build

print_status "Starting containers..."
docker-compose up -d

# Wait for the service to be ready
print_status "Waiting for service to start..."
sleep 10

# Check if the service is healthy
if curl -f http://localhost:8000/health &> /dev/null; then
    print_status "✅ Page Counter API is running successfully!"
    print_status "📊 API available at: http://localhost:8000"
    print_status "📖 Documentation at: http://localhost:8000/docs"
else
    print_error "❌ Service health check failed. Checking logs..."
    docker-compose logs page-counter
    exit 1
fi

# Display useful commands
echo ""
echo "🔧 Useful commands:"
echo "  View logs:        docker-compose logs -f page-counter"
echo "  Stop service:     docker-compose down"
echo "  Restart service:  docker-compose restart"
echo "  Update service:   docker-compose pull && docker-compose up -d"
echo ""

# Check available memory (important for Raspberry Pi)
AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.1fMB", $7}')
print_status "Available memory: $AVAILABLE_MEM"

if [[ $(free -m | awk 'NR==2{print $7}') -lt 200 ]]; then
    print_warning "Low memory detected. Consider increasing swap or reducing other services."
fi

# Show container status
print_status "Container status:"
docker-compose ps

echo ""
print_status "🎉 Deployment complete! Your Page Counter API is ready to use."
