#!/bin/bash
# Run integration tests against deployed API Gateway

set -e

echo "🧪 Running Integration Tests for Auth API"
echo "=========================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set API URL from environment or use default
export API_BASE_URL="${API_BASE_URL:-https://o06264kkzj.execute-api.us-east-1.amazonaws.com/prod}"

echo "Testing API: $API_BASE_URL"
echo ""

# Run tests with verbose output
pytest tests/integration/ -v --tb=short

echo ""
echo "✅ Integration tests complete!"
