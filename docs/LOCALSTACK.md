# LocalStack Development Guide

This guide covers using LocalStack for local AWS development with the Know-It-All Tutor System.

## Overview

LocalStack is a cloud service emulator that runs in a single container on your laptop or in your CI environment. It provides a fully functional local AWS cloud stack, allowing you to develop and test your cloud applications offline.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your App      │    │   LocalStack    │    │   PostgreSQL    │
│                 │    │                 │    │   Container     │
│ Lambda Functions│◄──►│ AWS Services    │◄──►│                 │
│ CDK Stacks      │    │ - Lambda        │    │ Database:       │
│ Tests           │    │ - RDS           │    │ tutor_system    │
│                 │    │ - S3            │    │                 │
│                 │    │ - API Gateway   │    │ Two Modes:      │
│                 │    │ - Secrets Mgr   │    │ • Direct        │
│                 │    │ - Cognito       │    │ • Via RDS       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       Port: 4566
```

## Two Development Modes

### Standard Mode (Direct PostgreSQL)
- **Connection**: Direct to PostgreSQL container
- **Use Case**: Simple development, faster startup
- **Command**: `make local-dev`

### RDS Emulation Mode (Recommended)
- **Connection**: PostgreSQL via LocalStack RDS service
- **Use Case**: Production parity, Aurora Serverless-like behavior
- **Command**: `make local-dev-rds`

## Prerequisites

Before starting, ensure you have:
- Docker and Docker Compose installed
- Python 3.11+ installed
- Git installed

## Database Configuration Options

### Option 1: Use Existing PostgreSQL (Recommended)

If you have PostgreSQL installed on your system, this is the recommended approach:

**Check if PostgreSQL is running:**
```bash
systemctl status postgresql
# or
pg_isready -h localhost -p 5432
```

**Advantages:**
- No port conflicts
- Uses your existing PostgreSQL installation
- Better performance (no Docker overhead)
- Easier to manage and backup

**Connection Details:**
- Host: localhost
- Port: 5432
- Database: tutor_system
- User: tutor_user
- Password: tutor_password

### Option 2: Use Containerized PostgreSQL

If you prefer to use a separate PostgreSQL container or don't have PostgreSQL installed:

**Advantages:**
- Complete isolation from system PostgreSQL
- Easy to reset and recreate
- Consistent across different environments

**Connection Details:**
- Host: localhost
- Port: 5433 (to avoid conflicts)
- Database: tutor_system
- User: tutor_user
- Password: tutor_password

**Note:** This option uses `docker-compose.localstack-with-db.yml` and requires updating `.env.localstack` to use port 5433.

## Quick Start

### First Time Setup

**For Option 1 (Existing PostgreSQL):**
```bash
# Complete setup (first time only)
make local-dev
```

This command does three things:
1. **Database Setup**: Creates `tutor_system` database and schema in PostgreSQL container
2. **LocalStack Start**: Starts LocalStack container on port 4566
3. **Resource Setup**: Creates AWS resources (S3 buckets, RDS instances, etc.)
4. **Mode Selection**: Choose between direct PostgreSQL or RDS emulation

### Daily Usage

After the first setup, you typically only need to start/stop LocalStack:

```bash
# Start LocalStack (daily usage)
make localstack-start

# Stop LocalStack when done
make localstack-stop
```

**Note:** Your PostgreSQL database persists between sessions, so you don't need to recreate it.

### When to Use `make local-dev`

- **First time setup** - Creates everything from scratch
- **After major changes** - If you need to recreate AWS resources
- **After database issues** - If you need to reset the database schema
- **New team member setup** - Complete environment initialization

### When to Use `make localstack-start`

- **Daily development** - Just start LocalStack services
- **After `make localstack-stop`** - Resume development
- **After system restart** - LocalStack container needs to be restarted

**For Option 2 (Containerized PostgreSQL):**
```bash
# First time setup
docker-compose -f docker-compose.localstack-with-db.yml up -d
make localstack-setup

# Daily usage
docker-compose -f docker-compose.localstack-with-db.yml up -d
# (Resources persist, so no need to run setup again)

# Stop when done
docker-compose -f docker-compose.localstack-with-db.yml down
```

### 2. Verify Setup
```bash
# Check LocalStack health
curl http://localhost:4566/health

# Check available services
make localstack-status

# Complete verification
make localstack-verify

# View logs
make localstack-logs
```

### 3. Run Tests
```bash
# Run tests against LocalStack
make local-test

# Run specific test categories
pytest tests/ -m "integration"
pytest tests/ -m "database"
```

## Configuration

### Environment Variables
LocalStack configuration is managed through `.env.localstack`:

```bash
# LocalStack Configuration
LOCALSTACK_ENDPOINT=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1

# Database Configuration
DATABASE_URL=postgresql://tutor_user:tutor_password@localhost:5432/tutor_system

# Application Configuration
ENVIRONMENT=local
LOG_LEVEL=DEBUG
```

### Docker Compose Configuration
The `docker-compose.localstack.yml` file defines:

- **LocalStack container**: AWS services emulation
- **PostgreSQL container**: Local database
- **Networking**: Shared network for service communication
- **Volumes**: Data persistence across restarts

### LocalStack Configuration File
The `localstack.yml` file configures:

- **Services**: Which AWS services to enable
- **Persistence**: Data retention between restarts
- **Lambda settings**: Execution environment
- **Debugging**: Logging and troubleshooting options

### Available Services

### AWS Services in LocalStack

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| Lambda | 4566 | Serverless functions | ✅ |
| S3 | 4566 | Object storage | ✅ |
| API Gateway | 4566 | REST APIs | ✅ |
| Secrets Manager | 4566 | Credential storage | ✅ |
| CloudWatch | 4566 | Logging/monitoring | ✅ |
| IAM | 4566 | Access management | ✅ |
| CloudFormation | 4566 | Infrastructure as Code | ✅ |
| Cognito IDP | 4566 | User authentication | ✅ |
| SES | 4566 | Email service | ✅ |

### Local Services

| Service | Port | Purpose | Credentials |
|---------|------|---------|-------------|
| PostgreSQL | 5432 | Relational database (system service) | tutor_user/tutor_password |
| MailHog SMTP | 1025 | Email testing server | test/test |
| MailHog Web UI | 8025 | Email inbox viewer | N/A |
| LocalStack Web UI | 4566 | Management interface | N/A |

## Switching Between Database Options

### From Containerized to System PostgreSQL
```bash
# Stop containers
make localstack-stop

# Setup system PostgreSQL
make database-setup

# Start LocalStack only
make localstack-start
make localstack-setup
```

### From System to Containerized PostgreSQL
```bash
# Stop LocalStack
make localstack-stop

# Start with containerized PostgreSQL
docker-compose -f docker-compose.localstack-with-db.yml up -d

# Update .env.localstack to use port 5433
# Edit: DB_PORT=5433

# Setup LocalStack resources
make localstack-setup
```

## Development Workflow

### 1. Daily Development
```bash
# Start your day (after first setup)
make localstack-start

# Make code changes
# ... edit files ...

# Test changes
make local-test

# Deploy to LocalStack (if using CDK)
cdk deploy --context environment=local

# End of day
make localstack-stop  # Stops LocalStack, PostgreSQL keeps running
```

### 2. First Time Setup Workflow
```bash
# Complete initial setup
make local-dev

# Verify everything works
make localstack-verify

# Start developing!
```

### 4. Testing Workflow
```bash
# Unit tests (no LocalStack needed)
pytest tests/unit/

# Integration tests (requires LocalStack)
make localstack-start
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/
```

## Command Reference

### Setup Commands (Run Once)
```bash
make local-dev          # Complete first-time setup
make database-setup     # Setup PostgreSQL database only
```

### Daily Commands
```bash
make localstack-start   # Start LocalStack
make localstack-stop    # Stop LocalStack
make localstack-status  # Check what's running
make localstack-verify  # Verify everything works
```

### Development Commands
```bash
make local-test         # Run tests against LocalStack
make localstack-logs    # View LocalStack logs
source scripts/activate_local_env.sh  # Activate development environment
```

### Troubleshooting Commands
```bash
make localstack-setup   # Recreate AWS resources
docker ps               # Check running containers
systemctl status postgresql  # Check PostgreSQL status
```

### 3. Debugging Workflow
```bash
# View LocalStack logs
make localstack-logs

# Check service health
curl http://localhost:4566/health

# Inspect resources
awslocal s3 ls
awslocal lambda list-functions
```

## Testing and Quality Assurance

### Comprehensive Testing Strategy

LocalStack enables comprehensive testing of AWS services without incurring costs or requiring internet connectivity. The testing strategy covers all AWS integrations with identical APIs to production.

#### Test Categories

**Unit Tests with LocalStack:**
```bash
# Test individual AWS service integrations
pytest tests/unit/test_secrets_manager.py
pytest tests/unit/test_kms_integration.py
pytest tests/unit/test_s3_operations.py
pytest tests/unit/test_lambda_functions.py
```

**Integration Tests:**
```bash
# Test complete workflows with multiple AWS services
make test-secrets           # Secrets Manager + KMS integration
make test-lambda-secrets    # Lambda function with encrypted credentials
make local-test            # Full integration test suite
```

**Property-Based Tests:**
```python
# Test system invariants across all possible inputs
from hypothesis import given, strategies as st
import boto3

@given(
    secret_name=st.text(min_size=5, max_size=50),
    secret_data=st.dictionaries(st.text(), st.text())
)
def test_secrets_roundtrip_property(secret_name, secret_data):
    """Any secret stored should be retrievable with identical data"""
    secrets_client = boto3.client(
        'secretsmanager',
        endpoint_url='http://localhost:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )
    
    # Store secret
    secrets_client.create_secret(
        Name=f'test-{secret_name}',
        SecretString=json.dumps(secret_data),
        KmsKeyId='alias/tutor-system-secrets'
    )
    
    # Retrieve and verify
    response = secrets_client.get_secret_value(SecretId=f'test-{secret_name}')
    retrieved_data = json.loads(response['SecretString'])
    
    assert retrieved_data == secret_data
```

#### Automated Testing Pipeline

**CI/CD Integration:**
```yaml
# GitHub Actions / CodeBuild integration
test_localstack:
  runs-on: ubuntu-latest
  steps:
    - name: Start LocalStack
      run: |
        docker-compose -f docker-compose.localstack.yml up -d
        sleep 30
    
    - name: Setup LocalStack Resources
      run: make localstack-setup
    
    - name: Run Integration Tests
      run: |
        export LOCALSTACK_ENDPOINT=http://localhost:4566
        make test-secrets
        make local-test
    
    - name: Verify All Services
      run: make localstack-verify
    
    - name: Cleanup
      run: make localstack-stop
```

### Testing Best Practices

#### Test Data Management
```python
# Fixture for consistent test setup
@pytest.fixture(scope="session")
def localstack_setup():
    """Setup LocalStack environment for testing"""
    # Wait for LocalStack to be ready
    wait_for_localstack()
    
    # Create test resources
    setup_test_secrets()
    setup_test_buckets()
    setup_test_lambda_functions()
    
    yield
    
    # Cleanup after tests
    cleanup_test_resources()

@pytest.fixture
def test_credentials():
    """Provide test credentials for AWS services"""
    return {
        'aws_access_key_id': 'test',
        'aws_secret_access_key': 'test',
        'region_name': 'us-east-1',
        'endpoint_url': 'http://localhost:4566'
    }
```

#### Error Scenario Testing
```python
def test_secrets_manager_error_handling():
    """Test graceful handling of Secrets Manager failures"""
    # Test network failure scenario
    with mock.patch('boto3.client') as mock_client:
        mock_client.side_effect = ConnectionError("Network unreachable")
        
        # Should fallback to environment variables
        db_config = get_database_credentials()
        assert db_config['host'] == os.getenv('DB_HOST')

def test_kms_decryption_failure():
    """Test handling of KMS decryption failures"""
    # Test insufficient permissions
    with mock.patch('boto3.client') as mock_client:
        mock_client.return_value.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'DecryptionFailureException'}}, 'GetSecretValue'
        )
        
        with pytest.raises(Exception, match="Cannot decrypt secret"):
            get_database_credentials()
```

### Performance Testing

#### Load Testing with LocalStack
```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

async def test_concurrent_secret_access():
    """Test concurrent access to Secrets Manager"""
    async def get_secret():
        # Simulate Lambda function accessing secrets
        credentials = await get_database_credentials()
        return credentials is not None
    
    # Test 50 concurrent requests
    tasks = [get_secret() for _ in range(50)]
    results = await asyncio.gather(*tasks)
    
    # All requests should succeed
    assert all(results)
    assert len(results) == 50

def test_lambda_cold_start_performance():
    """Test Lambda function cold start with secrets access"""
    import time
    
    start_time = time.time()
    
    # Invoke Lambda function that accesses secrets
    result = lambda_client.invoke(
        FunctionName='tutor-system-auth',
        Payload=json.dumps({'test': 'cold_start'})
    )
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Should complete within reasonable time
    assert execution_time < 5.0  # 5 seconds max
    assert result['StatusCode'] == 200
```

## Email Testing with Cognito

### MailHog Integration

The system uses **MailHog** for local email testing with Cognito. MailHog captures all emails sent by Cognito (verification emails, password reset emails, etc.) without actually sending them to real email addresses.

#### How It Works

1. **LocalStack Cognito** sends emails via SMTP to MailHog
2. **MailHog** captures emails and displays them in a web interface
3. **Developers** can view and test email content at `http://localhost:8025`

#### Email Testing Workflow

```bash
# Start LocalStack with MailHog
make local-dev

# Register a new user (triggers verification email)
curl -X POST http://localhost:4566/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123!"}'

# View the verification email
open http://localhost:8025

# Extract verification code from email and confirm registration
curl -X POST http://localhost:4566/api/auth/confirm \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "confirmationCode": "123456"}'
```

#### MailHog Web Interface

Access the MailHog web interface at `http://localhost:8025` to:

- **View all captured emails** in a Gmail-like interface
- **Read email content** (HTML and plain text)
- **Extract verification codes** for testing
- **Test email templates** and formatting
- **Debug email delivery issues**

#### Cognito Email Configuration

LocalStack automatically configures Cognito to use MailHog for email delivery:

```typescript
// Cognito automatically uses these settings in LocalStack
const emailConfig = {
  emailSendingAccount: 'DEVELOPER',
  sourceArn: 'arn:aws:ses:us-east-1:000000000000:identity/noreply@know-it-all-tutor.com',
  replyToEmailAddress: 'noreply@know-it-all-tutor.com',
  smtpSettings: {
    host: 'mailhog',
    port: 1025,
    username: 'test',
    password: 'test'
  }
}
```

### Email Testing Scenarios

#### 1. User Registration Flow
```bash
# Test complete registration with email verification
python3 scripts/test_cognito_registration.py
```

#### 2. Password Reset Flow
```bash
# Test forgot password email delivery
python3 scripts/test_cognito_password_reset.py
```

#### 3. Email Template Testing
```bash
# Test custom email templates
python3 scripts/test_cognito_email_templates.py
```

### Alternative Email Testing Options

#### Option 1: MailHog (Recommended)
- **Pros**: Visual interface, captures all emails, no configuration needed
- **Cons**: Requires additional container
- **Best for**: Development and manual testing

#### Option 2: LocalStack SES with File Output
```bash
# Configure LocalStack to save emails to files
export SES_EMAIL_BACKEND=file
export SES_EMAIL_FILE_PATH=/tmp/localstack/emails/
```

#### Option 3: Mock Email Service
```python
# Create a mock email service for automated testing
class MockEmailService:
    def __init__(self):
        self.sent_emails = []
    
    def send_email(self, to, subject, body):
        self.sent_emails.append({
            'to': to,
            'subject': subject,
            'body': body,
            'timestamp': datetime.now()
        })
    
    def get_latest_email(self, to_address):
        emails = [e for e in self.sent_emails if e['to'] == to_address]
        return emails[-1] if emails else None
```

### Testing Email Content

#### Verification Email Testing
```python
import requests
from bs4 import BeautifulSoup

def test_verification_email():
    # Register user
    response = requests.post('http://localhost:4566/api/auth/register', json={
        'email': 'test@example.com',
        'password': 'TestPass123!'
    })
    
    # Get email from MailHog API
    mailhog_response = requests.get('http://localhost:8025/api/v2/messages')
    emails = mailhog_response.json()['items']
    
    # Find verification email
    verification_email = next(
        email for email in emails 
        if 'test@example.com' in email['To'][0]['Mailbox']
    )
    
    # Extract verification code
    email_body = verification_email['Content']['Body']
    soup = BeautifulSoup(email_body, 'html.parser')
    verification_code = soup.find('strong').text
    
    # Confirm registration
    confirm_response = requests.post('http://localhost:4566/api/auth/confirm', json={
        'email': 'test@example.com',
        'confirmationCode': verification_code
    })
    
    assert confirm_response.status_code == 200
```

### Email Testing Commands

```bash
# Start email testing environment
make local-dev

# View MailHog interface
open http://localhost:8025

# Test Cognito email flows
make test-cognito-emails

# Clear all captured emails
curl -X DELETE http://localhost:8025/api/v1/messages

# Get email count
curl http://localhost:8025/api/v2/messages | jq '.total'

# Search for specific emails
curl "http://localhost:8025/api/v2/search?kind=to&query=test@example.com"
```

## Working with AWS Services

### Using AWS CLI with LocalStack
Install `awscli-local` for easier LocalStack interaction:

```bash
pip install awscli-local

# Use awslocal instead of aws
awslocal s3 ls
awslocal lambda invoke --function-name tutor-system-auth output.json
awslocal secretsmanager list-secrets
awslocal kms list-keys
```

### Using Boto3 with LocalStack
Configure boto3 clients to use LocalStack:

```python
import boto3

# Configure for LocalStack
client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

# Use normally
response = client.list_buckets()
```

### Secrets Manager Integration Examples

#### Retrieving Database Credentials
```python
from src.shared.secrets_client import get_database_credentials

# Automatically retrieves and decrypts credentials
credentials = get_database_credentials()
print(f"Database: {credentials['database']} at {credentials['host']}")
```

#### Lambda Function with Secrets
```python
# Example Lambda function using encrypted credentials
import json
from src.shared.secrets_client import get_database_credentials, get_jwt_config
from src.shared.database import get_db_cursor

def lambda_handler(event, context):
    try:
        # Get encrypted credentials (automatically KMS decrypted)
        db_creds = get_database_credentials()
        jwt_config = get_jwt_config()
        
        # Use credentials for database operations
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully accessed encrypted credentials',
                'user_count': user_count,
                'security': {
                    'credentials_source': 'AWS Secrets Manager',
                    'encryption': 'KMS encrypted'
                }
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

#### Testing Secrets Integration
```bash
# Test the complete secrets integration
python3 scripts/test_secrets_integration.py

# Test KMS + Secrets Manager specifically
python3 scripts/test_kms_secrets.py

# Test Lambda function with secrets
python3 src/lambda_functions/example_secrets_usage/handler.py
```

### CDK with LocalStack
Deploy CDK stacks to LocalStack:

```bash
# Set LocalStack endpoint
export CDK_DEFAULT_ACCOUNT=000000000000
export CDK_DEFAULT_REGION=us-east-1

# Bootstrap (one time)
cdklocal bootstrap

# Deploy
cdklocal deploy TutorSystemStack-local
```

## Troubleshooting

### Common Issues

#### LocalStack Won't Start
```bash
# Check Docker is running
docker ps

# Check port conflicts
lsof -i :4566
lsof -i :5432

# Restart with clean state
make localstack-stop
docker system prune -f
make local-dev
```

#### Services Not Available
```bash
# Check LocalStack health
curl http://localhost:4566/health

# Restart LocalStack
make localstack-stop
make localstack-start
make localstack-setup
```

#### PostgreSQL Port Conflict
```bash
# Check what's using port 5432
ss -tlnp | grep :5432

# If system PostgreSQL is running (recommended approach)
make local-dev  # Uses existing PostgreSQL

# Alternative: Use containerized PostgreSQL on different port
docker-compose -f docker-compose.localstack-with-db.yml up -d
# Update .env.localstack to use port 5433
```

#### LocalStack Won't Start
```bash
# Check Docker is running
docker ps

# Check port conflicts
lsof -i :4566

# Restart with clean state
make localstack-stop
docker system prune -f
make local-dev
```

#### Services Not Available
```bash
# Check LocalStack health
curl http://localhost:4566/health

# Restart LocalStack
make localstack-stop
make localstack-start
make localstack-setup
```

#### Database Connection Issues
```bash
# Check PostgreSQL is running (system service)
systemctl status postgresql

# Test connection
psql -h localhost -p 5432 -U tutor_user -d tutor_system

# Reset database schema
make database-setup
```

#### Lambda Function Issues
```bash
# Check Lambda logs
awslocal logs describe-log-groups
awslocal logs get-log-events --log-group-name /aws/lambda/function-name

# Redeploy function
awslocal lambda update-function-code --function-name my-function --zip-file fileb://function.zip
```

### Performance Tips

1. **Use Persistence**: Enable data persistence to avoid re-setup
2. **Selective Services**: Only enable needed AWS services
3. **Resource Limits**: Set appropriate Docker memory limits
4. **Cleanup**: Regularly clean up unused resources

### Debugging Tips

1. **Enable Debug Logging**: Set `DEBUG=1` in LocalStack
2. **Use LocalStack Logs**: Monitor container logs for issues
3. **Check Health Endpoint**: Verify service availability
4. **Use AWS CLI Local**: Test services directly

## Integration with CI/CD

### GitHub Actions Example
```yaml
name: Test with LocalStack
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start LocalStack
        run: |
          docker-compose -f docker-compose.localstack.yml up -d
          sleep 30
      
      - name: Setup LocalStack
        run: make localstack-setup
      
      - name: Run Tests
        run: make local-test
      
      - name: Stop LocalStack
        run: make localstack-stop
```

## Best Practices

### Development
1. **Always use LocalStack for local development**
2. **Keep LocalStack configuration in version control**
3. **Use environment-specific configurations**
4. **Test against LocalStack before deploying to AWS**
5. **Use existing PostgreSQL service when available**
6. **Implement comprehensive secrets management testing**

### Testing
1. **Write tests that work with both LocalStack and AWS**
2. **Use fixtures for test data setup**
3. **Clean up resources after tests**
4. **Use appropriate test markers for different environments**
5. **Test all AWS service integrations with LocalStack**
6. **Validate Secrets Manager + KMS integration thoroughly**

### Database Management
1. **Use system PostgreSQL when available (port 5432)**
2. **Use containerized PostgreSQL only if needed (port 5433)**
3. **Keep database schema in version control**
4. **Use migrations for schema changes**
5. **Test database connections with encrypted credentials**

### Security
1. **Never commit real AWS credentials**
2. **Use test credentials for LocalStack**
3. **Keep sensitive data in environment variables**
4. **Regularly update LocalStack version**
5. **Test IAM policies and KMS encryption locally**
6. **Validate secrets rotation and access patterns**

### Key Rotation Policies

The system implements environment-specific key rotation policies:

#### Local Development (LocalStack)
- **Rotation Interval**: Every 2 days
- **Purpose**: Rapid testing of rotation procedures
- **Secrets Rotated**: Database credentials, JWT secrets
- **Configuration**: Automatic via LocalStack setup

#### AWS Production
- **Rotation Interval**: Every 6 months (180 days)
- **Purpose**: Industry standard for production security
- **Secrets Rotated**: Database credentials, JWT secrets
- **Configuration**: Automatic via AWS Secrets Manager

#### Testing Rotation Policies
```bash
# Test LocalStack rotation configuration
make test-rotation

# Test AWS rotation configuration
make test-rotation-aws

# Configure missing rotation policies
make configure-rotation

# Manual testing
python3 scripts/test_rotation_policy.py --localstack
python3 scripts/test_rotation_policy.py --configure
```

#### Rotation Policy Details
- **Database Credentials**: Automatically rotated using Lambda function
- **JWT Secrets**: Rotated to maintain security without service interruption
- **KMS Keys**: Annual rotation enabled for all encryption keys
- **Validation**: Automated testing ensures rotation works correctly
- **Monitoring**: CloudWatch alerts on rotation failures

### Secrets Management
1. **Always use Secrets Manager for credentials in Lambda functions**
2. **Test KMS encryption and decryption workflows**
3. **Implement proper error handling for secrets access failures**
4. **Use environment-specific secret naming conventions**
5. **Validate IAM policies for secrets access**
6. **Test credential rotation scenarios**

## Resources

- [LocalStack Documentation](https://docs.localstack.cloud/)
- [LocalStack GitHub](https://github.com/localstack/localstack)
- [AWS CLI Local](https://github.com/localstack/awscli-local)
- [CDK Local](https://github.com/localstack/aws-cdk-local)

## Support

For LocalStack-specific issues:
1. Check the [LocalStack documentation](https://docs.localstack.cloud/)
2. Search [LocalStack GitHub issues](https://github.com/localstack/localstack/issues)
3. Join the [LocalStack Slack community](https://localstack.cloud/contact/)

For project-specific issues:
1. Check this documentation
2. Review the project's issue tracker
3. Ask the development team