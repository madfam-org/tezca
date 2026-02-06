#!/bin/bash
set -e

echo "🚀 Starting Leyes Como Código Development Environment..."

# Check for Docker
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose is not installed."
    exit 1
fi

# Build and start services
echo "📦 Building and starting services..."
docker-compose up -d --build

echo "✅ Services started!"
echo "   - Frontend: http://localhost:3000"
echo "   - API:      http://localhost:8000/api/v1/"
echo "   - Search:   http://localhost:9200"
echo ""
echo "📝 To view logs: docker-compose logs -f"
