#!/usr/bin/env python3
"""
Create a Lambda layer with psycopg2 for LocalStack using AWS Lambda compatible binaries
"""
import zipfile
import io
import subprocess
import tempfile
import os
import urllib.request
from pathlib import Path

def download_lambda_psycopg2():
    """Download pre-compiled psycopg2 for AWS Lambda"""
    
    print("📥 Downloading AWS Lambda compatible psycopg2...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Download psycopg2 compiled for AWS Lambda
        # This is a known working version for Lambda runtime
        psycopg2_url = "https://files.pythonhosted.org/packages/fd/ae/98cb7a0cbb1d748ee547b058b14604bd0e9bf285a8e0cc5d148f8a8a9eb44/psycopg2_binary-2.9.5-cp39-cp39-linux_x86_64.whl"
        
        whl_file = temp_path / "psycopg2.whl"
        
        try:
            urllib.request.urlretrieve(psycopg2_url, whl_file)
            print(f"✅ Downloaded psycopg2 wheel")
        except Exception as e:
            print(f"❌ Failed to download: {e}")
            return None
        
        # Extract the wheel
        python_path = temp_path / "python"
        python_path.mkdir()
        
        # Extract wheel contents
        with zipfile.ZipFile(whl_file, 'r') as wheel:
            wheel.extractall(python_path)
        
        # Create layer zip
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in python_path.rglob('*'):
                if file_path.is_file():
                    arc_name = str(file_path.relative_to(temp_path))
                    zip_file.write(file_path, arc_name)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

def create_psycopg2_layer():
    """Create a Lambda layer with psycopg2-binary"""
    
    print("🔧 Creating Lambda layer with psycopg2...")
    
    # Try downloading Lambda-compatible version first
    layer_content = download_lambda_psycopg2()
    if layer_content:
        return layer_content
    
    # Fallback to pip install
    print("📦 Falling back to pip install...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        python_path = temp_path / "python"
        python_path.mkdir()
        
        # Install psycopg2-binary to the layer directory
        try:
            subprocess.run([
                "pip", "install", "psycopg2-binary==2.9.5", 
                "--target", str(python_path),
                "--platform", "linux_x86_64",
                "--only-binary=:all:",
                "--no-deps"
            ], check=True)
        except subprocess.CalledProcessError:
            print("⚠️ Pip install failed, trying without platform specification...")
            subprocess.run([
                "pip", "install", "psycopg2-binary==2.9.5", 
                "--target", str(python_path),
                "--only-binary=:all:",
                "--no-deps"
            ], check=True)
        
        # Create zip file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in python_path.rglob('*'):
                if file_path.is_file():
                    arc_name = str(file_path.relative_to(temp_path))
                    zip_file.write(file_path, arc_name)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

def deploy_layer():
    """Deploy the psycopg2 layer to LocalStack"""
    import boto3
    
    lambda_client = boto3.client(
        'lambda',
        endpoint_url='http://localhost:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1'
    )
    
    layer_content = create_psycopg2_layer()
    
    try:
        # Delete existing layer versions first
        try:
            lambda_client.delete_layer_version(
                LayerName='psycopg2-layer',
                VersionNumber=1
            )
            print("🗑️ Deleted existing layer version")
        except:
            pass
        
        response = lambda_client.publish_layer_version(
            LayerName='psycopg2-layer',
            Description='PostgreSQL driver for Lambda functions (AWS compatible)',
            Content={'ZipFile': layer_content},
            CompatibleRuntimes=['python3.9', 'python3.10', 'python3.11']
        )
        
        layer_arn = response['LayerVersionArn']
        print(f"✅ Created Lambda layer: {layer_arn}")
        return layer_arn
        
    except Exception as e:
        print(f"❌ Failed to create layer: {e}")
        return None

if __name__ == "__main__":
    deploy_layer()