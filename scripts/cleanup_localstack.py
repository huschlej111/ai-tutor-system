#!/usr/bin/env python3
"""
Clean up LocalStack resources and prepare for real AWS deployment
"""
import subprocess
import os
from pathlib import Path

def stop_localstack():
    """Stop LocalStack containers"""
    print("🛑 Stopping LocalStack...")
    try:
        subprocess.run(['make', 'localstack-stop'], check=True)
        print("✅ LocalStack stopped")
    except subprocess.CalledProcessError:
        print("⚠️ LocalStack may not be running")

def cleanup_temp_files():
    """Clean up temporary files created during LocalStack testing"""
    print("🧹 Cleaning up temporary files...")
    
    files_to_remove = [
        'test_lambda_direct.py',
        'test_simple_lambda.py',
        'test_payload.json',
        'response.json',
        'simple_response.json',
        'scripts/create_lambda_layer.py'
    ]
    
    for file_path in files_to_remove:
        if Path(file_path).exists():
            Path(file_path).unlink()
            print(f"   Removed {file_path}")
    
    print("✅ Cleanup completed")

def reset_frontend_config():
    """Reset frontend configuration for AWS deployment"""
    print("🔧 Resetting frontend configuration...")
    
    # Keep the real Cognito configuration but remove LocalStack API URL
    env_content = """# Real AWS Cognito configuration
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=us-east-1_xvY9wcTTf
VITE_COGNITO_USER_POOL_CLIENT_ID=3osourf1ea1qig29qqc3r138pb

# Use real AWS (not LocalStack)
VITE_USE_REAL_AWS_COGNITO=true

# API URL will be set after AWS deployment
VITE_API_BASE_URL=
VITE_NODE_ENV=development
"""
    
    with open('frontend/.env.local', 'w') as f:
        f.write(env_content)
    
    print("✅ Frontend configuration reset")

def main():
    """Main cleanup function"""
    print("🧹 Cleaning up LocalStack environment")
    print("=" * 40)
    
    stop_localstack()
    cleanup_temp_files()
    reset_frontend_config()
    
    print("\n" + "=" * 40)
    print("✅ LocalStack cleanup completed!")
    print("\n📋 Ready for AWS deployment:")
    print("1. Run: python scripts/deploy_to_aws.py")
    print("2. This will deploy to real AWS infrastructure")
    print("3. No more LocalStack limitations!")

if __name__ == "__main__":
    main()