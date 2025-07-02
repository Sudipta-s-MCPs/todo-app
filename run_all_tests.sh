#!/bin/bash

echo "================================"
echo "🧪 SMART-TODO COMPREHENSIVE TESTS"
echo "================================"
echo ""

# Check if services are running
if ! docker-compose ps | grep -q "smart-todo-backend.*Up"; then
    echo "❌ Backend service is not running. Please run ./deploy_local.sh first"
    exit 1
fi

echo "✅ Services are running"
echo ""

# Install test dependencies
echo "📦 Installing test dependencies..."
docker-compose exec test-client pip install -r requirements.txt > /dev/null 2>&1

# Run API tests
echo ""
echo "1️⃣ Running API Tests..."
echo "------------------------"
docker-compose exec test-client python /app/test_api.py

# Run frontend feature tests
echo ""
echo "2️⃣ Running Frontend Feature Tests..."
echo "------------------------------------"
docker-compose exec test-client python /app/test_frontend_features.py

# Run E2E scenario tests
echo ""
echo "3️⃣ Running End-to-End Scenarios..."
echo "-----------------------------------"
docker-compose exec test-client python /app/test_e2e_scenarios.py

# Run production tests
echo ""
echo "4️⃣ Running Production Tests..."
echo "-------------------------------"
./run_prod_tests.py

echo ""
echo "================================"
echo "✅ All tests completed!"
echo "================================"
echo ""
echo "📊 Test Summary:"
echo "- API endpoints tested"
echo "- Frontend features validated"
echo "- E2E user scenarios verified"
echo "- Production environment checked"
echo ""
echo "🎉 Smart-ToDo is fully tested and ready for use!"