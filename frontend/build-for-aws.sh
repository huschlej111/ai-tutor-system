#!/bin/bash
# Build frontend for AWS deployment with production environment variables

# Get values from CDK outputs (you'll need to update these after first deploy)
export VITE_AWS_REGION="us-east-1"
export VITE_COGNITO_USER_POOL_ID="us-east-1_xapIGvbJE"
export VITE_COGNITO_USER_POOL_CLIENT_ID="2jcn4r8irqqq2ckb6oas965v49"
export VITE_API_BASE_URL="https://o06264kkzj.execute-api.us-east-1.amazonaws.com/prod"
export VITE_NODE_ENV="production"

echo "Building frontend with AWS configuration..."
echo "  Region: $VITE_AWS_REGION"
echo "  User Pool: $VITE_COGNITO_USER_POOL_ID"
echo "  API URL: $VITE_API_BASE_URL"

npm run build

echo "✅ Build complete! Output in dist/"
