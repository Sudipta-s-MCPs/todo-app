#!/bin/bash
# Production deployment script for Synology NAS
# Uses external PostgreSQL and Redis from NAS

echo "🚀 Deploying Smart-ToDo to Production (Synology NAS)"
echo "📅 Date: $(date)"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "   Run: cp .env.example .env"
    echo "   Then edit .env with your production values"
    exit 1
fi

# Pull latest images
echo "📦 Pulling latest images..."
docker-compose pull

# Start backend, frontend, and admin-panel (no local postgres/redis)
echo "🔄 Starting services..."
docker-compose up -d backend frontend admin-panel

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Deployment complete!"
echo "🌐 Services available at:"
echo "   - Backend API: http://192.168.11.100:5482"
echo "   - Admin Panel: http://192.168.11.100:5483"
echo "   - Frontend App: http://192.168.11.100:5484"
echo "   - API Docs: http://192.168.11.100:5482/docs"
echo ""
echo "📝 To view logs: docker-compose logs -f"
echo "🧪 To run tests: ./run_prod_tests.py --api-url http://192.168.11.100:5482"