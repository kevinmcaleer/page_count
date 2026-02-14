#!/bin/bash

# Simple Page Counter - Raspberry Pi Quick Deploy

echo "🍓 Simple Page Counter - Raspberry Pi Deployment"
echo "==============================================="

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "⚠️  Please logout and login again, then re-run this script"
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Installing..."
    sudo pip3 install docker-compose
fi

# Create data directory
echo "📁 Creating data directory..."
mkdir -p ./data

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.simple.yml down 2>/dev/null || true

# Build and start
echo "🚀 Building and starting Page Counter..."
docker-compose -f docker-compose.simple.yml up --build -d

# Wait and test
echo "⏳ Waiting for service to start..."
sleep 10

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ SUCCESS! Page Counter is running!"
    echo ""
    echo "🌐 Access your app:"
    echo "   http://localhost:8000/docs    (API documentation)"
    echo "   http://localhost:8000/stats   (View statistics)"
    echo ""
    echo "🧪 Test it:"
    echo "   curl 'http://localhost:8000/?url=https://example.com'"
    echo ""
    echo "📊 View logs: docker-compose -f docker-compose.simple.yml logs -f"
    echo "🛑 Stop app: docker-compose -f docker-compose.simple.yml down"
else
    echo "❌ FAILED! Check logs:"
    docker-compose -f docker-compose.simple.yml logs
fi

echo ""
echo "🎉 Deployment complete!"
