#!/usr/bin/env python3
"""
Deploy the tutor system to real AWS infrastructure for UAT
This uses the CDK infrastructure defined in infrastructure/
"""
import subprocess
import sys
import os
from pathlib import Path
import json

def check_aws_credentials():
    """Check if AWS credentials are configured"""
    try:
        result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                              capture_output=True, text=True, check=True)
        identity = json.loads(result.stdout)
        print(f"✅ AWS credentials configured for: {identity.get('Arn', 'Unknown')}")
        return True
    except subprocess.CalledProcessError:
        print("❌ AWS credentials not configured. Run 'aws configure' first.")
        return False
    except FileNotFoundError:
        print("❌ AWS CLI not installed. Install it first.")
        return False

def check_cdk_installed():
    """Check if CDK is installed"""
    try:
        result = subprocess.run(['cdk', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ CDK installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ CDK not installed. Run 'npm install -g aws-cdk' first.")
        return False

def bootstrap_cdk():
    """Bootstrap CDK if needed"""
    try:
        print("🔧 Bootstrapping CDK...")
        subprocess.run(['cdk', 'bootstrap'], check=True, cwd='infrastructure')
        print("✅ CDK bootstrapped successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ CDK bootstrap failed: {e}")
        return False

def install_dependencies():
    """Install Python dependencies for Lambda functions"""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def deploy_infrastructure():
    """Deploy the CDK infrastructure"""
    print("🚀 Deploying infrastructure to AWS...")
    try:
        # Deploy the main stack
        result = subprocess.run([
            'cdk', 'deploy', 'TutorSystemStack', 
            '--require-approval', 'never',
            '--outputs-file', 'cdk-outputs.json'
        ], check=True, cwd='infrastructure', capture_output=True, text=True)
        
        print("✅ Infrastructure deployed successfully")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Infrastructure deployment failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def get_deployment_outputs():
    """Get the deployment outputs"""
    outputs_file = Path('infrastructure/cdk-outputs.json')
    if outputs_file.exists():
        with open(outputs_file, 'r') as f:
            outputs = json.load(f)
        return outputs
    return {}

def update_frontend_config(outputs):
    """Update frontend configuration with real AWS endpoints"""
    print("🔧 Updating frontend configuration...")
    
    # Extract relevant outputs
    stack_outputs = outputs.get('TutorSystemStack', {})
    api_url = stack_outputs.get('ApiGatewayUrl')
    user_pool_id = stack_outputs.get('UserPoolId')
    user_pool_client_id = stack_outputs.get('UserPoolClientId')
    
    if not all([api_url, user_pool_id, user_pool_client_id]):
        print("⚠️ Some outputs missing, using existing Cognito configuration")
        api_url = api_url or "https://your-api-gateway-url"
        user_pool_id = user_pool_id or "us-east-1_xvY9wcTTf"  # Existing real Cognito
        user_pool_client_id = user_pool_client_id or "3osourf1ea1qig29qqc3r138pb"
    
    # Update frontend environment
    env_content = f"""# Production AWS configuration
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID={user_pool_id}
VITE_COGNITO_USER_POOL_CLIENT_ID={user_pool_client_id}

# Use real AWS (not LocalStack)
VITE_USE_REAL_AWS_COGNITO=true

VITE_API_BASE_URL={api_url}
VITE_NODE_ENV=production
"""
    
    with open('frontend/.env.production', 'w') as f:
        f.write(env_content)
    
    print(f"✅ Frontend configured for production")
    print(f"   API URL: {api_url}")
    print(f"   Cognito User Pool: {user_pool_id}")
    
    return True

def main():
    """Main deployment function"""
    print("🚀 Deploying Know-It-All Tutor System to AWS")
    print("=" * 50)
    
    # Pre-flight checks
    if not check_aws_credentials():
        return 1
    
    if not check_cdk_installed():
        return 1
    
    if not install_dependencies():
        return 1
    
    # Bootstrap CDK if needed
    if not bootstrap_cdk():
        return 1
    
    # Deploy infrastructure
    if not deploy_infrastructure():
        return 1
    
    # Get outputs and update frontend
    outputs = get_deployment_outputs()
    if not update_frontend_config(outputs):
        return 1
    
    print("\n" + "=" * 50)
    print("✅ Deployment completed successfully!")
    print("\n📋 Next steps:")
    print("1. Build and deploy frontend:")
    print("   cd frontend && npm run build")
    print("2. Test the application with real AWS services")
    print("3. The system is now running on production AWS infrastructure")
    
    # Print important URLs
    stack_outputs = outputs.get('TutorSystemStack', {})
    if stack_outputs:
        print(f"\n🌐 Important URLs:")
        if 'ApiGatewayUrl' in stack_outputs:
            print(f"   API Gateway: {stack_outputs['ApiGatewayUrl']}")
        if 'DatabaseEndpoint' in stack_outputs:
            print(f"   Database: {stack_outputs['DatabaseEndpoint']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())