#!/bin/bash
# Local development deployment script
# Uses local PostgreSQL and Redis containers

echo "🚀 Starting Smart-ToDo in Local Development Mode"
echo "📅 Date: $(date)"
echo "=================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your local development values"
fi

# Start all services including local postgres and redis
echo "🔄 Starting all services with local profile..."
COMPOSE_PROFILES=local docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 15

# Initialize database if needed
echo "🗄️ Checking database..."
docker-compose exec backend python scripts/init_db.py || echo "Database already initialized"

# Check service status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Local deployment complete!"
echo "🌐 Services available at:"
echo "   - Backend API: http://localhost:5482"
echo "   - Admin Panel: http://localhost:5483"
echo "   - Frontend App: http://localhost:5484"
echo "   - API Docs: http://localhost:5482/docs"
echo "   - PostgreSQL: localhost:15432"
echo "   - Redis: localhost:16379"
echo ""
echo "🔑 Default admin credentials:"
echo "   Email: admin@example.com"
echo "   Password: admin123"
echo ""
echo "📝 To view logs: docker-compose logs -f"
echo "🧪 To run tests: ./run_prod_tests.py"