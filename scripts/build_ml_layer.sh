#!/bin/bash
set -e

# Build ML Model Lambda Layer Script
# This script creates a Lambda layer containing the ML model and Python dependencies
# for the Answer Evaluator Lambda function

echo "🚀 Starting ML Model Layer Build Process..."

# Configuration
LAYER_DIR="layer"
ML_MODEL_DIR="layer/ml_model"
PYTHON_DIR="layer/python"
ZIP_FILE="ml_model_layer.zip"
S3_BUCKET="${S3_BUCKET:-tutor-ml-layers}"
LAYER_NAME="${LAYER_NAME:-tutor-ml-model-layer}"
REGION="${AWS_REGION:-us-east-1}"
SOURCE_MODEL_DIR="final_similarity_model"

# Clean up previous build
echo "🧹 Cleaning up previous build artifacts..."
rm -rf "$LAYER_DIR"
rm -f "$ZIP_FILE"

# Step 1: Create directory structure
echo "📁 Creating directory structure..."
mkdir -p "$ML_MODEL_DIR"
mkdir -p "$PYTHON_DIR"

# Step 2: Copy model files from final_similarity_model/
echo "📦 Copying ML model files from $SOURCE_MODEL_DIR/..."
if [ ! -d "$SOURCE_MODEL_DIR" ]; then
    echo "❌ Error: Source model directory '$SOURCE_MODEL_DIR' not found!"
    echo "Please ensure the model files are in the '$SOURCE_MODEL_DIR' directory."
    exit 1
fi

cp -r "$SOURCE_MODEL_DIR"/* "$ML_MODEL_DIR/"
echo "✅ Model files copied successfully"

# Step 3: Install Python dependencies using Docker for Lambda compatibility
echo "🐍 Installing Python dependencies using Docker (Lambda-compatible)..."
echo "   - torch (CPU-only)"
echo "   - sentence-transformers==3.3.1"
echo "   - transformers==4.57.3"
echo "   - scikit-learn==1.6.1"
echo "   - numpy==2.2.2"

# Create a temporary requirements file
cat > /tmp/ml_layer_requirements.txt << EOF
torch --index-url https://download.pytorch.org/whl/cpu
sentence-transformers==3.3.1
transformers==4.57.3
scikit-learn==1.6.1
numpy==2.2.2
EOF

# Use official AWS Lambda Python 3.12 image for compatibility
docker run --rm \
    -v "$(pwd)/$PYTHON_DIR":/var/task \
    -v /tmp/ml_layer_requirements.txt:/tmp/requirements.txt \
    public.ecr.aws/lambda/python:3.12 \
    pip install -r /tmp/requirements.txt -t /var/task

echo "✅ Python dependencies installed"

# Step 4: Create zip file
echo "📦 Creating zip file..."
cd "$LAYER_DIR"
zip -r "../$ZIP_FILE" . -q
cd ..

# Get zip file size
ZIP_SIZE=$(stat -f%z "$ZIP_FILE" 2>/dev/null || stat -c%s "$ZIP_FILE" 2>/dev/null)
ZIP_SIZE_MB=$((ZIP_SIZE / 1024 / 1024))

echo "✅ Zip file created: $ZIP_FILE (${ZIP_SIZE_MB}MB)"

# Step 5: Upload to S3 if size > 50MB
if [ $ZIP_SIZE_MB -gt 50 ]; then
    echo "📤 Layer size (${ZIP_SIZE_MB}MB) exceeds 50MB, uploading to S3..."
    
    # Create S3 bucket if it doesn't exist
    if ! aws s3 ls "s3://$S3_BUCKET" 2>/dev/null; then
        echo "Creating S3 bucket: $S3_BUCKET"
        aws s3 mb "s3://$S3_BUCKET" --region "$REGION"
    fi
    
    # Upload to S3
    S3_KEY="layers/$LAYER_NAME/$(date +%Y%m%d-%H%M%S)/$ZIP_FILE"
    aws s3 cp "$ZIP_FILE" "s3://$S3_BUCKET/$S3_KEY" --region "$REGION"
    echo "✅ Uploaded to s3://$S3_BUCKET/$S3_KEY"
    
    # Step 6: Publish Lambda layer version from S3
    echo "🚀 Publishing Lambda layer version from S3..."
    LAYER_VERSION=$(aws lambda publish-layer-version \
        --layer-name "$LAYER_NAME" \
        --description "ML Model Layer with sentence-transformers for answer evaluation" \
        --content "S3Bucket=$S3_BUCKET,S3Key=$S3_KEY" \
        --compatible-runtimes python3.12 \
        --region "$REGION" \
        --query 'Version' \
        --output text)
    
    LAYER_ARN=$(aws lambda get-layer-version \
        --layer-name "$LAYER_NAME" \
        --version-number "$LAYER_VERSION" \
        --region "$REGION" \
        --query 'LayerVersionArn' \
        --output text)
else
    # Step 6: Publish Lambda layer version directly
    echo "🚀 Publishing Lambda layer version directly (size < 50MB)..."
    LAYER_VERSION=$(aws lambda publish-layer-version \
        --layer-name "$LAYER_NAME" \
        --description "ML Model Layer with sentence-transformers for answer evaluation" \
        --zip-file "fileb://$ZIP_FILE" \
        --compatible-runtimes python3.12 \
        --region "$REGION" \
        --query 'Version' \
        --output text)
    
    LAYER_ARN=$(aws lambda get-layer-version \
        --layer-name "$LAYER_NAME" \
        --version-number "$LAYER_VERSION" \
        --region "$REGION" \
        --query 'LayerVersionArn' \
        --output text)
fi

echo ""
echo "✅ ML Model Layer Build Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Layer Name:    $LAYER_NAME"
echo "Layer Version: $LAYER_VERSION"
echo "Layer ARN:     $LAYER_ARN"
echo "Layer Size:    ${ZIP_SIZE_MB}MB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Use this ARN in your CDK stack to attach the layer to Lambda functions"
echo ""
