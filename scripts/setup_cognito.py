#!/usr/bin/env python3
"""
Setup Cognito User Pool and App Client for LocalStack
Creates the exact Cognito resources expected by the frontend
"""
import json
import boto3
from botocore.exceptions import ClientError


def setup_cognito():
    """Create Cognito User Pool and App Client in LocalStack"""
    
    # Configure for LocalStack
    cognito = boto3.client(
        'cognito-idp',
        endpoint_url='http://localhost:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1'
    )
    
    # Expected User Pool ID and App Client ID from frontend config
    expected_user_pool_id = 'us-east-1_EXAMPLE123'
    expected_client_id = 'abcdef123456789example'
    
    print("🔐 Setting up Cognito User Pool and App Client...")
    
    try:
        # Create User Pool with specific ID (LocalStack allows this)
        user_pool_response = cognito.create_user_pool(
            PoolName='TutorSystemUserPool',
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
            AliasAttributes=['email'],
            UsernameAttributes=['email'],
            EmailConfiguration={
                'EmailSendingAccount': 'DEVELOPER',
                'SourceArn': 'arn:aws:ses:us-east-1:000000000000:identity/noreply@know-it-all-tutor.com',
                'ReplyToEmailAddress': 'noreply@know-it-all-tutor.com'
            },
            VerificationMessageTemplate={
                'DefaultEmailOption': 'CONFIRM_WITH_CODE',
                'EmailSubject': 'Know-It-All Tutor - Verify your email',
                'EmailMessage': 'Welcome to Know-It-All Tutor! Your verification code is {####}'
            },
            UserPoolTags={
                'Environment': 'local',
                'Application': 'know-it-all-tutor'
            }
        )
        
        user_pool_id = user_pool_response['UserPool']['Id']
        print(f"✅ Created User Pool: {user_pool_id}")
        
        # Create App Client with specific ID (LocalStack allows this)
        app_client_response = cognito.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName='TutorSystemWebClient',
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
        
        # In LocalStack, we need to manually set the IDs to match frontend expectations
        # This is a LocalStack-specific workaround
        print(f"\n📝 Frontend expects:")
        print(f"   User Pool ID: {expected_user_pool_id}")
        print(f"   App Client ID: {expected_client_id}")
        print(f"\n📝 LocalStack created:")
        print(f"   User Pool ID: {user_pool_id}")
        print(f"   App Client ID: {client_id}")
        
        # Create some test users
        create_test_users(cognito, user_pool_id)
        
        print(f"\n✅ Cognito setup completed!")
        print(f"🌐 User Pool ID: {user_pool_id}")
        print(f"🔑 App Client ID: {client_id}")
        
        # Update frontend environment if needed
        update_frontend_env(user_pool_id, client_id)
        
        return user_pool_id, client_id
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print("✅ Cognito User Pool already exists")
            # Try to get existing pool info
            try:
                pools = cognito.list_user_pools(MaxResults=10)
                for pool in pools['UserPools']:
                    if pool['Name'] == 'TutorSystemUserPool':
                        user_pool_id = pool['Id']
                        print(f"✅ Found existing User Pool: {user_pool_id}")
                        
                        # Get app clients
                        clients = cognito.list_user_pool_clients(UserPoolId=user_pool_id)
                        if clients['UserPoolClients']:
                            client_id = clients['UserPoolClients'][0]['ClientId']
                            print(f"✅ Found existing App Client: {client_id}")
                            return user_pool_id, client_id
                        break
            except Exception as list_error:
                print(f"⚠️ Could not list existing pools: {list_error}")
        else:
            print(f"❌ Failed to create Cognito resources: {e}")
            raise


def create_test_users(cognito, user_pool_id):
    """Create test users for development"""
    test_users = [
        {
            'username': 'admin@example.com',
            'email': 'admin@example.com',
            'given_name': 'Admin',
            'family_name': 'User',
            'temporary_password': 'TempPass123!',
            'permanent_password': 'admin123'
        },
        {
            'username': 'test@example.com',
            'email': 'test@example.com',
            'given_name': 'Test',
            'family_name': 'User',
            'temporary_password': 'TempPass123!',
            'permanent_password': 'test123'
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
            
            # Confirm user (mark as verified)
            cognito.admin_confirm_sign_up(
                UserPoolId=user_pool_id,
                Username=user['username']
            )
            
            print(f"✅ Created test user: {user['email']} (password: {user['permanent_password']})")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                print(f"✅ Test user already exists: {user['email']}")
            else:
                print(f"⚠️ Failed to create test user {user['email']}: {e}")


def update_frontend_env(user_pool_id, client_id):
    """Update frontend environment file with actual Cognito IDs"""
    env_file = 'frontend/.env.local'
    
    try:
        env_content = f"""# Local development configuration
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID={user_pool_id}
VITE_COGNITO_USER_POOL_CLIENT_ID={client_id}

VITE_API_BASE_URL=http://localhost:4566
VITE_NODE_ENV=development
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"✅ Updated {env_file} with actual Cognito IDs")
        print("🔄 Please restart the frontend server to pick up new environment variables")
        
    except Exception as e:
        print(f"⚠️ Could not update frontend environment file: {e}")
        print(f"📝 Please manually update {env_file} with:")
        print(f"   VITE_COGNITO_USER_POOL_ID={user_pool_id}")
        print(f"   VITE_COGNITO_USER_POOL_CLIENT_ID={client_id}")


def main():
    """Main entry point"""
    try:
        setup_cognito()
    except Exception as e:
        print(f"❌ Cognito setup failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())