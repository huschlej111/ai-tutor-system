#!/bin/bash
# Activate local development environment for Know-It-All Tutor System

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Activating Local Development Environment${NC}"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install boto3 requests localstack awscli-local psycopg2-binary
else
    echo -e "${GREEN}✅ Activating virtual environment${NC}"
    source venv/bin/activate
fi

# Load environment variables
if [ -f ".env.localstack" ]; then
    echo -e "${GREEN}✅ Loading LocalStack environment variables${NC}"
    export $(cat .env.localstack | xargs)
else
    echo -e "${YELLOW}⚠️  .env.localstack not found${NC}"
fi

echo ""
echo -e "${GREEN}🎯 Environment Ready!${NC}"
echo ""
echo "Available commands:"
echo "  awslocal s3 ls                    # List S3 buckets"
echo "  awslocal dynamodb list-tables     # List DynamoDB tables"
echo "  awslocal lambda list-functions    # List Lambda functions"
echo "  awslocal secretsmanager list-secrets  # List secrets"
echo ""
echo "Services:"
echo "  LocalStack: http://localhost:4566"
echo "  PostgreSQL: localhost:5432"
echo ""
echo "To deactivate: deactivate"