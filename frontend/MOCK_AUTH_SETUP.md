# Mock Authentication Setup

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
