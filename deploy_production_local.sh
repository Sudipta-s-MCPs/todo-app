#!/bin/bash
# Production deployment script for Linux with nginx proxy
# Uses external PostgreSQL and Redis from Synology NAS
# Nginx proxies domains to local ports

echo "🚀 Deploying Smart-ToDo in Production Mode (Linux with nginx proxy)"
echo "📅 Date: $(date)"
echo "=================================================="

# Check if production env file exists
if [ ! -f .env.production ]; then
    echo "❌ Error: .env.production file not found!"
    exit 1
fi

# Use production environment
echo "📋 Loading production environment..."
cp .env.production .env

# Build images locally
echo "🔨 Building Docker images..."
docker-compose build

# Start all services
echo "🔄 Starting all services..."
docker-compose up -d backend frontend admin-panel mcp-server

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 15

# Initialize database if needed
echo "🗄️ Checking database..."
docker-compose exec backend python scripts/init_db.py || echo "Database already initialized"

# Initialize settings if needed
echo "⚙️ Initializing application settings..."
docker-compose exec backend python scripts/init_settings.py || echo "Settings already initialized"

# Check service status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Production deployment complete!"
echo ""
echo "🌐 Services available via nginx proxy:"
echo "   - Frontend App: https://todo.sudiptadhara.in"
echo "   - Admin Panel: https://todo-admin.sudiptadhara.in"
echo "   - Backend API: https://todo-api.sudiptadhara.in"
echo "   - MCP Server: https://todo-mcp.sudiptadhara.in"
echo ""
echo "🔌 Local services (nginx proxies to these):"
echo "   - Backend: http://localhost:5482"
echo "   - Admin: http://localhost:5483"
echo "   - Frontend: http://localhost:5484"
echo "   - MCP: http://localhost:5485"
echo ""
echo "📊 External services:"
echo "   - PostgreSQL: 192.168.11.100:15432"
echo "   - Redis: 192.168.11.100:6379"
echo ""
echo "🔑 Admin credentials:"
echo "   Email: sudiptai26.889@gmail.com"
echo "   (Use the admin panel to create/manage users)"
echo ""
echo "📝 Commands:"
echo "   View logs: docker-compose logs -f"
echo "   Run tests: ./run_prod_tests.py --api-url https://todo-api.sudiptadhara.in"
echo "   Stop services: docker-compose down"