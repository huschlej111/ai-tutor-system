#!/usr/bin/env python3
"""
Setup real AWS Cognito for local development
This creates actual AWS resources for testing
"""
import json
import boto3
from botocore.exceptions import ClientError
import os


def setup_real_cognito():
    """Create real Cognito User Pool and App Client in AWS"""
    
    # Use real AWS (not LocalStack)
    cognito = boto3.client('cognito-idp', region_name='us-east-1')
    
    print("🔐 Setting up REAL AWS Cognito for local development...")
    print("⚠️  This will create actual AWS resources and may incur costs")
    
    # Confirm with user
    response = input("Continue with real AWS Cognito setup? (y/N): ")
    if response.lower() != 'y':
        print("❌ Setup cancelled")
        return False
    
    try:
        # Create User Pool
        user_pool_response = cognito.create_user_pool(
            PoolName='TutorSystemUserPool-Dev',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': False
                }
            },
            AutoVerifiedAttributes=['email'],
            UsernameAttributes=['email'],  # Use email as username
            EmailConfiguration={
                'EmailSendingAccount': 'COGNITO_DEFAULT'
            },
            VerificationMessageTemplate={
                'DefaultEmailOption': 'CONFIRM_WITH_CODE',
                'EmailSubject': 'Know-It-All Tutor - Verify your email',
                'EmailMessage': 'Welcome to Know-It-All Tutor! Your verification code is {####}'
            },
            UserPoolTags={
                'Environment': 'development',
                'Application': 'know-it-all-tutor',
                'Purpose': 'local-development'
            }
        )
        
        user_pool_id = user_pool_response['UserPool']['Id']
        print(f"✅ Created User Pool: {user_pool_id}")
        
        # Create App Client
        app_client_response = cognito.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName='TutorSystemWebClient-Dev',
            GenerateSecret=False,  # Public client for web app
            RefreshTokenValidity=30,
            AccessTokenValidity=60,
            IdTokenValidity=60,
            TokenValidityUnits={
                'AccessToken': 'minutes',
                'IdToken': 'minutes',
                'RefreshToken': 'days'
            },
            ReadAttributes=[
                'email',
                'email_verified',
                'given_name',
                'family_name',
                'preferred_username'
            ],
            WriteAttributes=[
                'email',
                'given_name',
                'family_name',
                'preferred_username'
            ],
            ExplicitAuthFlows=[
                'ALLOW_USER_SRP_AUTH',
                'ALLOW_USER_PASSWORD_AUTH',
                'ALLOW_REFRESH_TOKEN_AUTH'
            ],
            PreventUserExistenceErrors='ENABLED',
            EnableTokenRevocation=True
        )
        
        client_id = app_client_response['UserPoolClient']['ClientId']
        print(f"✅ Created App Client: {client_id}")
        
        # Update frontend environment
        update_frontend_env(user_pool_id, client_id)
        
        # Create test users
        create_test_users(cognito, user_pool_id)
        
        print(f"\n✅ Real AWS Cognito setup completed!")
        print(f"🌐 User Pool ID: {user_pool_id}")
        print(f"🔑 App Client ID: {client_id}")
        print(f"\n⚠️  Remember to delete these resources when done to avoid charges:")
        print(f"   aws cognito-idp delete-user-pool --user-pool-id {user_pool_id}")
        
        return True
        
    except ClientError as e:
        print(f"❌ Failed to create Cognito resources: {e}")
        return False


def create_test_users(cognito, user_pool_id):
    """Create test users in real Cognito"""
    test_users = [
        {
            'username': 'admin@example.com',
            'email': 'admin@example.com',
            'given_name': 'Admin',
            'family_name': 'User',
            'temporary_password': 'TempPass123!',
            'permanent_password': 'Admin123!'
        },
        {
            'username': 'test@example.com',
            'email': 'test@example.com',
            'given_name': 'Test',
            'family_name': 'User',
            'temporary_password': 'TempPass123!',
            'permanent_password': 'Test123!'
        }
    ]
    
    print("\n👥 Creating test users...")
    
    for user in test_users:
        try:
            # Create user
            cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=user['username'],
                UserAttributes=[
                    {'Name': 'email', 'Value': user['email']},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'given_name', 'Value': user['given_name']},
                    {'Name': 'family_name', 'Value': user['family_name']}
                ],
                TemporaryPassword=user['temporary_password'],
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            
            # Set permanent password
            cognito.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=user['username'],
                Password=user['permanent_password'],
                Permanent=True
            )
            
            print(f"✅ Created test user: {user['email']} (password: {user['permanent_password']})")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                print(f"✅ Test user already exists: {user['email']}")
            else:
                print(f"⚠️ Failed to create test user {user['email']}: {e}")


def update_frontend_env(user_pool_id, client_id):
    """Update frontend environment file with real Cognito IDs"""
    env_file = 'frontend/.env.local'
    
    env_content = f"""# Local development configuration - REAL AWS COGNITO
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID={user_pool_id}
VITE_COGNITO_USER_POOL_CLIENT_ID={client_id}

# Use real AWS (not LocalStack) for Cognito
VITE_USE_REAL_AWS_COGNITO=true

VITE_API_BASE_URL=http://localhost:4566
VITE_NODE_ENV=development
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"✅ Updated {env_file} with real Cognito IDs")
        print("🔄 Please restart the frontend server to pick up new environment variables")
        
    except Exception as e:
        print(f"⚠️ Could not update frontend environment file: {e}")


def cleanup_cognito():
    """Clean up Cognito resources"""
    print("🧹 Cleaning up Cognito resources...")
    
    # This would list and delete user pools created by this script
    # Implementation left as exercise for safety
    print("⚠️  Please manually delete Cognito resources to avoid charges")
    print("   Use AWS Console or CLI to delete the User Pool")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Real AWS Cognito setup for local development")
    parser.add_argument("--cleanup", action="store_true", help="Clean up resources")
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_cognito()
        return 0
    
    success = setup_real_cognito()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())