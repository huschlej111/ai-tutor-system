#!/bin/bash
set -e

# Deploy ML Model Lambda with Docker Container
# This approach has no size limits (10GB vs 250MB for layers)

echo "🚀 Starting ML Model Lambda Container Deployment..."

# Configuration
REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="${FUNCTION_NAME:-answer-evaluator}"
REPO_NAME="${REPO_NAME:-answer-evaluator}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:latest"
LAMBDA_DIR="lambda/answer-evaluator"

# Step 1: Create Lambda directory structure if it doesn't exist
echo "📁 Setting up Lambda directory structure..."
mkdir -p "$LAMBDA_DIR"

# Step 2: Create Lambda function code
echo "📝 Creating Lambda function code..."
cat > "$LAMBDA_DIR/lambda_function.py" << 'EOF'
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import json

# Load model once (outside handler for reuse across invocations)
model = None

def load_model():
    global model
    if model is None:
        print("Loading model...")
        model = SentenceTransformer('/opt/ml/model/')
        print("Model loaded successfully")
    return model

def handler(event, context):
    """
    Evaluate semantic similarity between student answer and correct answer
    
    Input: {
        "answer": "student's answer text",
        "correct_answer": "expected answer text"
    }
    
    Output: {
        "similarity": 0.85,
        "feedback": "Excellent match!"
    }
    """
    try:
        # Parse input (handle both API Gateway and direct invocation)
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        answer = body.get('answer', '').strip()
        correct_answer = body.get('correct_answer', '').strip()
        
        if not answer or not correct_answer:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Both answer and correct_answer are required'})
            }
        
        # Load model
        model = load_model()
        
        # Generate embeddings
        embeddings = model.encode([answer, correct_answer])
        
        # Calculate similarity
        similarity = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
        
        # Generate feedback based on similarity score
        if similarity >= 0.85:
            feedback = "Excellent! Your answer matches the expected response."
        elif similarity >= 0.70:
            feedback = "Good answer, but could be more precise."
        elif similarity >= 0.50:
            feedback = "Partially correct. Review the key concepts."
        else:
            feedback = "Incorrect. Please review the material."
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'similarity': round(similarity, 4),
                'feedback': feedback
            })
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
EOF

# Step 3: Create requirements.txt
echo "📝 Creating requirements.txt..."
cat > "$LAMBDA_DIR/requirements.txt" << 'EOF'
sentence-transformers==3.3.1
transformers==4.57.3
scikit-learn==1.6.1
EOF

# Step 4: Create Dockerfile
echo "📝 Creating Dockerfile..."
cat > "$LAMBDA_DIR/Dockerfile" << 'EOF'
FROM public.ecr.aws/lambda/python:3.12

# Copy model files (will be copied from build context)
COPY final_similarity_model/ /opt/ml/model/

# Install PyTorch CPU-only first
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies from PyPI
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Lambda function
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Set handler
CMD ["lambda_function.handler"]
EOF

echo "✅ Lambda files created in $LAMBDA_DIR/"

# Step 5: Create ECR repository if it doesn't exist
echo "📦 Setting up ECR repository..."
if aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$REGION" 2>/dev/null; then
    echo "Repository $REPO_NAME already exists"
else
    aws ecr create-repository --repository-name "$REPO_NAME" --region "$REGION"
    echo "✅ Created ECR repository: $REPO_NAME"
fi

# Step 6: Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region "$REGION" | \
    docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Step 7: Build Docker image
echo "🏗️  Building Docker image..."
# Copy model to build context
cp -r final_similarity_model "$LAMBDA_DIR/"
cd "$LAMBDA_DIR"
docker build --platform linux/amd64 -t "$REPO_NAME:latest" .
cd ../..
# Clean up copied model
rm -rf "$LAMBDA_DIR/final_similarity_model"

# Get image size
IMAGE_SIZE=$(docker images "$REPO_NAME:latest" --format "{{.Size}}")
echo "✅ Image built: $IMAGE_SIZE"

# Step 8: Tag and push to ECR
echo "📤 Pushing image to ECR..."
docker tag "$REPO_NAME:latest" "$IMAGE_URI"
docker push "$IMAGE_URI"
echo "✅ Image pushed to ECR"

# Step 9: Create or update Lambda function
echo "⚡ Deploying Lambda function..."

# Check if function exists
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --image-uri "$IMAGE_URI" \
        --region "$REGION"
    
    # Wait for update to complete
    echo "Waiting for function update to complete..."
    aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
else
    echo "Creating new function..."
    
    # Create execution role if needed
    ROLE_NAME="${FUNCTION_NAME}-role"
    
    if aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
        ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
        echo "Using existing role: $ROLE_ARN"
    else
        echo "Creating IAM role..."
        ROLE_ARN=$(aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document '{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }' \
            --query 'Role.Arn' \
            --output text)
        
        # Attach basic execution policy
        aws iam attach-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        
        # Wait for role to propagate
        echo "Waiting for IAM role to propagate..."
        sleep 10
    fi
    
    # Create function
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --package-type Image \
        --code ImageUri="$IMAGE_URI" \
        --role "$ROLE_ARN" \
        --memory-size 2048 \
        --timeout 30 \
        --region "$REGION"
    
    # Wait for function to be active
    echo "Waiting for function to be active..."
    aws lambda wait function-active --function-name "$FUNCTION_NAME" --region "$REGION"
fi

# Step 10: Test the function
echo ""
echo "🧪 Testing Lambda function..."
TEST_PAYLOAD='{"answer":"AWS Lambda is a serverless compute service","correct_answer":"Lambda is a serverless computing service"}'

aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload "$TEST_PAYLOAD" \
    --region "$REGION" \
    response.json > /dev/null

if [ -f response.json ]; then
    echo "Test Response:"
    cat response.json | python3 -m json.tool
    rm response.json
fi

echo ""
echo "✅ ML Model Lambda Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Function Name: $FUNCTION_NAME"
echo "Image URI:     $IMAGE_URI"
echo "Image Size:    $IMAGE_SIZE"
echo "Region:        $REGION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Invoke with:"
echo "aws lambda invoke --function-name $FUNCTION_NAME \\"
echo "  --payload '{\"answer\":\"test\",\"correct_answer\":\"test\"}' \\"
echo "  --region $REGION response.json"
echo ""
echo "📝 Next steps:"
echo "  1. Connect to API Gateway for HTTP access"
echo "  2. Configure VPC if database access needed"
echo "  3. Set up CloudWatch alarms for monitoring"
echo ""
