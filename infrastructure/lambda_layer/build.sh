#!/bin/bash
# Build Lambda layer using Docker to ensure compatibility with Lambda runtime

set -e

echo "Building Lambda layer with Docker..."

# Build the Docker image
docker build -t lambda-layer-builder .

# Create a container and copy the built layer
docker create --name temp-layer lambda-layer-builder
docker cp temp-layer:/asset/python ./python
docker rm temp-layer

echo "✅ Lambda layer built successfully in ./python/"
echo "Deploy with: cdk deploy --app 'python app.py' TutorSystemStack-dev"
