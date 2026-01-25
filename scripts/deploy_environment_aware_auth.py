#!/usr/bin/env python3
"""
Deploy environment-aware authentication system
Supports both LocalStack (local) and AWS (prod) deployments
"""
import os
import sys
import subprocess
import json
import argparse
from pathlib import Path


def run_command(command: str, cwd: str = None) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"


def deploy_to_localstack():
    """Deploy to LocalStack with local environment configuration"""
    print("🚀 Deploying environment-aware authentication to LocalStack...")
    print()
    
    # Set environment variables for LocalStack
    env_vars = {
        'CDK_DEFAULT_ACCOUNT': '000000000000',
        'CDK_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'test',
        'AWS_SECRET_ACCESS_KEY': 'test',
        'AWS_DEFAULT_REGION': 'us-east-1'
    }
    
    # Update environment
    os.environ.update(env_vars)
    
    print("📋 LocalStack Configuration:")
    print("   Stage: local")
    print("   Cognito Authorizer: Disabled")
    print("   JWT Verification: Manual decode without signature verification")
    print("   Authentication: Real Cognito tokens, local validation")
    print()
    
    # Bootstrap CDK for LocalStack
    print("🔧 Bootstrapping CDK for LocalStack...")
    exit_code, stdout, stderr = run_command(
        "cdklocal bootstrap",
        cwd="infrastructure"
    )
    
    if exit_code != 0:
        print(f"❌ CDK bootstrap failed: {stderr}")
        return False
    
    print("✅ CDK bootstrap completed")
    
    # Deploy the stack
    print("🚀 Deploying TutorSystemStack to LocalStack...")
    exit_code, stdout, stderr = run_command(
        "cdklocal deploy TutorSystemStack-local --context environment=local --require-approval never --outputs-file ../cdk-outputs-local.json",
        cwd="infrastructure"
    )
    
    if exit_code != 0:
        print(f"❌ CDK deployment failed: {stderr}")
        return False
    
    print("✅ LocalStack deployment completed!")
    
    # Display outputs
    try:
        with open("cdk-outputs-local.json", "r") as f:
            outputs = json.load(f)
            
        print()
        print("📋 Deployment Outputs:")
        stack_outputs = outputs.get("TutorSystemStack-local", {})
        
        if "APIGatewayURL" in stack_outputs:
            print(f"   API Gateway URL: {stack_outputs['APIGatewayURL']}")
        if "UserPoolId" in stack_outputs:
            print(f"   Cognito User Pool ID: {stack_outputs['UserPoolId']}")
        if "UserPoolClientId" in stack_outputs:
            print(f"   Cognito Client ID: {stack_outputs['UserPoolClientId']}")
            
    except FileNotFoundError:
        print("⚠️  Could not read deployment outputs")
    
    print()
    print("🎯 Next Steps:")
    print("   1. Update frontend/.env.local with the API Gateway URL")
    print("   2. Test authentication with: make test-auth-local")
    print("   3. Start frontend: cd frontend && npm run dev")
    
    return True


def deploy_to_production():
    """Deploy to production AWS with full authorization"""
    print("🚀 Deploying environment-aware authentication to Production AWS...")
    print()
    
    print("📋 Production Configuration:")
    print("   Stage: prod")
    print("   Cognito Authorizer: Enabled")
    print("   JWT Verification: Full Cognito validation")
    print("   Authentication: Cognito User Pool Authorizer on all protected endpoints")
    print()
    
    # Bootstrap CDK for AWS
    print("🔧 Bootstrapping CDK for AWS...")
    exit_code, stdout, stderr = run_command(
        "cdk bootstrap",
        cwd="infrastructure"
    )
    
    if exit_code != 0:
        print(f"❌ CDK bootstrap failed: {stderr}")
        return False
    
    print("✅ CDK bootstrap completed")
    
    # Deploy the stack
    print("🚀 Deploying TutorSystemStack to Production...")
    exit_code, stdout, stderr = run_command(
        "cdk deploy TutorSystemStack-prod --context environment=prod --require-approval never --outputs-file ../cdk-outputs-prod.json",
        cwd="infrastructure"
    )
    
    if exit_code != 0:
        print(f"❌ CDK deployment failed: {stderr}")
        return False
    
    print("✅ Production deployment completed!")
    
    # Display outputs
    try:
        with open("cdk-outputs-prod.json", "r") as f:
            outputs = json.load(f)
            
        print()
        print("📋 Deployment Outputs:")
        stack_outputs = outputs.get("TutorSystemStack-prod", {})
        
        if "APIGatewayURL" in stack_outputs:
            print(f"   API Gateway URL: {stack_outputs['APIGatewayURL']}")
        if "UserPoolId" in stack_outputs:
            print(f"   Cognito User Pool ID: {stack_outputs['UserPoolId']}")
        if "UserPoolClientId" in stack_outputs:
            print(f"   Cognito Client ID: {stack_outputs['UserPoolClientId']}")
            
    except FileNotFoundError:
        print("⚠️  Could not read deployment outputs")
    
    print()
    print("🎯 Next Steps:")
    print("   1. Update frontend environment with production API Gateway URL")
    print("   2. Configure Cognito User Pool in frontend")
    print("   3. Test production authentication flow")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Deploy environment-aware authentication system")
    parser.add_argument(
        "environment",
        choices=["local", "prod"],
        help="Target environment: 'local' for LocalStack, 'prod' for AWS"
    )
    
    args = parser.parse_args()
    
    if args.environment == "local":
        success = deploy_to_localstack()
    else:
        success = deploy_to_production()
    
    if success:
        print()
        print("🎉 Environment-aware authentication deployment completed successfully!")
        print()
        print("🔧 How it works:")
        print("   • Frontend always uses real AWS Cognito for authentication")
        print("   • Backend adapts based on STAGE environment variable:")
        print("     - local: Manually decodes JWT without signature verification")
        print("     - prod: Uses Cognito User Pool Authorizer for full validation")
        print("   • Same code works in both environments with different security models")
        sys.exit(0)
    else:
        print()
        print("❌ Deployment failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()