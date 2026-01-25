#!/usr/bin/env python3
"""
Setup mock authentication for local development
Since Cognito isn't available in LocalStack Community Edition
"""
import json
import os
from pathlib import Path


def create_mock_cognito_config():
    """Create mock Cognito configuration for frontend"""
    
    # Use mock IDs that match frontend expectations
    mock_user_pool_id = 'us-east-1_EXAMPLE123'
    mock_client_id = 'abcdef123456789example'
    
    print("🔐 Setting up mock authentication for local development...")
    print("⚠️  Note: Cognito is not available in LocalStack Community Edition")
    print("   Using mock authentication service instead")
    
    # Update frontend environment
    env_file = Path('frontend/.env.local')
    env_content = f"""# Local development configuration - MOCK AUTH
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID={mock_user_pool_id}
VITE_COGNITO_USER_POOL_CLIENT_ID={mock_client_id}

# Mock auth flag
VITE_USE_MOCK_AUTH=true

VITE_API_BASE_URL=http://localhost:4566
VITE_NODE_ENV=development
"""
    
    try:
        env_file.write_text(env_content)
        print(f"✅ Updated {env_file} with mock auth configuration")
    except Exception as e:
        print(f"❌ Failed to update frontend environment: {e}")
        return False
    
    # Create mock auth service configuration
    mock_config = {
        "userPoolId": mock_user_pool_id,
        "clientId": mock_client_id,
        "region": "us-east-1",
        "mockUsers": [
            {
                "username": "admin@example.com",
                "email": "admin@example.com",
                "password": "admin123",
                "given_name": "Admin",
                "family_name": "User",
                "email_verified": True
            },
            {
                "username": "test@example.com", 
                "email": "test@example.com",
                "password": "test123",
                "given_name": "Test",
                "family_name": "User",
                "email_verified": True
            }
        ]
    }
    
    # Save mock config for potential use by backend
    mock_config_file = Path('tmp/mock-auth-config.json')
    mock_config_file.parent.mkdir(exist_ok=True)
    
    try:
        mock_config_file.write_text(json.dumps(mock_config, indent=2))
        print(f"✅ Created mock auth config: {mock_config_file}")
    except Exception as e:
        print(f"❌ Failed to create mock config: {e}")
        return False
    
    print("\n🎯 Mock Authentication Setup Complete!")
    print("\n📝 Test Accounts:")
    print("  admin@example.com / admin123")
    print("  test@example.com / test123")
    print("\n⚠️  Important Notes:")
    print("  - This is MOCK authentication for local development only")
    print("  - No real email verification or password reset")
    print("  - All authentication is simulated")
    print("  - For production, use real AWS Cognito")
    print("\n🔄 Next Steps:")
    print("  1. Restart the frontend server: cd frontend && npm run dev")
    print("  2. Try logging in with the test accounts above")
    print("  3. Registration will work but won't send real emails")
    
    return True


def create_mock_auth_instructions():
    """Create instructions for implementing mock auth in frontend"""
    
    instructions_file = Path('frontend/MOCK_AUTH_SETUP.md')
    instructions_content = """# Mock Authentication Setup

Since Cognito is not available in LocalStack Community Edition, this project uses mock authentication for local development.

## How It Works

1. **Frontend Configuration**: Uses mock Cognito IDs that don't actually exist
2. **Mock Users**: Pre-defined test users for development
3. **Simulated Flow**: Authentication flow is simulated, not real

## Test Accounts

- **Admin**: admin@example.com / admin123
- **Test User**: test@example.com / test123

## Implementation Notes

The frontend should detect the `VITE_USE_MOCK_AUTH=true` environment variable and:

1. **Skip real Cognito calls** for authentication
2. **Use mock JWT tokens** for session management
3. **Simulate email verification** (no real emails sent)
4. **Allow any registration** (all users are "verified")

## For Production

- Remove `VITE_USE_MOCK_AUTH` environment variable
- Use real AWS Cognito User Pool and App Client
- Implement proper email verification and password reset

## Development Workflow

1. Start LocalStack: `make localstack-start`
2. Setup resources: `python3 scripts/setup_mock_auth.py`
3. Start frontend: `cd frontend && npm run dev`
4. Login with test accounts above

## Security Note

⚠️ **This is for LOCAL DEVELOPMENT ONLY**
- Never use mock authentication in production
- All authentication is simulated and insecure
- Real AWS Cognito should be used for production deployment
"""
    
    try:
        instructions_file.write_text(instructions_content)
        print(f"✅ Created mock auth instructions: {instructions_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to create instructions: {e}")
        return False


def main():
    """Main entry point"""
    print("🚀 Setting up mock authentication for local development...")
    
    success = True
    success &= create_mock_cognito_config()
    success &= create_mock_auth_instructions()
    
    if success:
        print("\n✅ Mock authentication setup completed successfully!")
        return 0
    else:
        print("\n❌ Mock authentication setup failed!")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())