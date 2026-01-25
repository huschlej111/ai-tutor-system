# ✅ LocalStack Setup Complete!

Your Know-It-All Tutor System is now configured with LocalStack RDS emulation for Aurora Serverless-like development.

## 🔐 Authentication Setup

### LocalStack Free Tier (Mock Authentication)
Since Cognito is not available in LocalStack's free tier, the system uses **mock authentication** for local development:

- **Mock Users**: `admin@example.com` / `admin123`, `test@example.com` / `test123`
- **No Real Email**: Email verification and password reset are simulated
- **Development Only**: This is for local development only - never use in production

### LocalStack Paid Tiers (Real Cognito)
If you have a LocalStack paid subscription (Base/Ultimate), the system can use real Cognito:

- **Real User Pools**: Full Cognito functionality
- **Email Integration**: With MailHog for local email testing
- **Production Parity**: Matches AWS Cognito behavior

## 🎯 RDS Emulation Mode

This setup provides:
- **PostgreSQL**: Connection through LocalStack RDS service
- **Aurora Serverless-like behavior**: Production parity
- **RDS features**: Parameter groups, connection pooling, RDS APIs
- **Secrets Manager integration**: Database credentials management

## 🚀 Quick Start

```bash
# Start RDS emulation development environment
make local-dev

# This sets up:
# - PostgreSQL container (via LocalStack RDS)
# - LocalStack with RDS instance management
# - Aurora Serverless-like behavior
# - MailHog for email testing
```

## 🎯 What's Been Set Up

### ✅ LocalStack Services
- **S3**: Object storage with 4 pre-configured buckets
- **RDS**: PostgreSQL instance emulation (Aurora Serverless-like)
- **Lambda**: Serverless functions (4 test functions created)
- **Secrets Manager**: Secure credential storage with database credentials
- **API Gateway**: REST API endpoints
- **CloudWatch**: Logging and monitoring
- **IAM**: Identity and access management
- **Authentication**: Mock authentication (Cognito requires paid LocalStack tier)

### ✅ Database Configuration

#### RDS Emulation (Aurora Serverless-like)
- **RDS Instance**: `tutor-system-db`
- **Engine**: PostgreSQL 15.4
- **Connection**: Via LocalStack RDS endpoint (localhost:4566)
- **Credentials**: Stored in Secrets Manager
- **Features**: Parameter groups, connection pooling, RDS APIs

### ✅ Database Schema
- **Tables**: Users, domains, terms, user_progress, quiz_sessions
- **Sample Data**: Pre-loaded test users and AWS fundamentals domain
- **Schema**: Automatically initialized on container startup

## 🔧 Available Commands

### Development Environment
```bash
# Start RDS emulation development environment
make local-dev

# Stop LocalStack
make localstack-stop

# Check status
make localstack-status
```

### Testing & Validation
```bash
# Test LocalStack services
make localstack-verify

# Test RDS connectivity
make test-rds

# Test database credentials from Secrets Manager
make test-rds-secret

# Test mock authentication (free tier)
# Login with: admin@example.com / admin123 or test@example.com / test123
```

### Setup & Management
```bash
# Setup LocalStack resources with RDS
make localstack-setup-rds

# View logs
make localstack-logs
```

## 🌐 Service Endpoints

### LocalStack Gateway
- **URL**: http://localhost:4566
- **Health Check**: http://localhost:4566/health
- **Web UI**: http://localhost:4566/_localstack/health

### Database Connections

#### RDS Emulation Mode
```bash
# Via LocalStack RDS (Aurora Serverless-like)
postgresql://tutor_user:tutor_password@localhost:4566/tutor_system?options=-c%20rds-instance-id=tutor-system-db
```

### Email Testing
- **MailHog Web UI**: http://localhost:8025
- **SMTP Server**: localhost:1025
- **Note**: Only works with LocalStack paid tiers (Cognito required)

## 🔑 Environment Configuration

### `.env.localstack` - RDS Emulation
```bash
# RDS emulation connection
DATABASE_URL=postgresql://tutor_user:tutor_password@localhost:4566/tutor_system?options=-c%20rds-instance-id=tutor-system-db
RDS_INSTANCE_IDENTIFIER=tutor-system-db
DB_SECRET_NAME=tutor-system/database/credentials
LOCALSTACK_ENDPOINT=http://localhost:4566

# Mock authentication (LocalStack free tier)
VITE_USE_MOCK_AUTH=true
VITE_COGNITO_USER_POOL_ID=us-east-1_123456789
VITE_COGNITO_USER_POOL_CLIENT_ID=abcdef123456789
```

## 🚀 Quick Start Commands

### RDS Emulation Mode
```bash
# Start with RDS emulation
make local-dev

# Test RDS connectivity
make test-rds

# Test database credentials from Secrets Manager
make test-rds-secret

# Verify setup
make localstack-verify
```

### Stop Services
```bash
# Stop LocalStack (PostgreSQL container remains)
make localstack-stop
```

## 🔧 Using LocalStack

### AWS CLI (Local)
```bash
# Use awslocal instead of aws
awslocal s3 ls
awslocal lambda list-functions
awslocal secretsmanager list-secrets

# RDS commands (RDS mode only)
awslocal rds describe-db-instances
awslocal rds describe-db-parameter-groups
```

### Python/Boto3

#### Standard Configuration
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

#### RDS Mode - Database Credentials from Secrets Manager
```python
import boto3
import json

# Get database credentials from Secrets Manager
secrets_client = boto3.client(
    'secretsmanager',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

secret = secrets_client.get_secret_value(
    SecretId='tutor-system/database/credentials'
)
db_creds = json.loads(secret['SecretString'])

# Use credentials for database connection
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    port=4566,  # LocalStack RDS endpoint
    database=db_creds['dbname'],
    user=db_creds['username'],
    password=db_creds['password'],
    options=f"-c rds-instance-id={db_creds['dbInstanceIdentifier']}"
)
```

### Database Access

#### RDS Mode
```bash
# Connect via LocalStack RDS endpoint
psql "postgresql://tutor_user:tutor_password@localhost:4566/tutor_system?options=-c%20rds-instance-id=tutor-system-db"
```

## 📊 Available Resources

### S3 Buckets
- `tutor-system-uploads-local` - User uploads
- `tutor-system-static-local` - Static assets  
- `tutor-system-ml-models-local` - ML model storage
- `tutor-system-backups-local` - Database backups (versioned)

### Lambda Functions
- `tutor-system-auth` - Authentication
- `tutor-system-quiz` - Quiz management
- `tutor-system-progress` - Progress tracking
- `tutor-system-ml-inference` - ML model inference

### RDS Resources (RDS Mode Only)
- **RDS Instance**: `tutor-system-db` (PostgreSQL 15.4)
- **DB Subnet Group**: `tutor-system-subnet-group`
- **Parameter Group**: `tutor-system-postgres15` (optimized settings)

### Secrets Manager
- `tutor-system/database/credentials` - Database connection info (RDS mode)
- `tutor-system/jwt` - JWT configuration
- `tutor-system/ml-model` - ML model settings

## 🧪 Testing

### RDS Mode
```bash
# Test RDS connectivity
make test-rds

# Test Secrets Manager integration
make test-rds-secret

# Run integration tests with RDS
source venv/bin/activate
export $(cat .env.localstack | xargs)
pytest tests/test_localstack_integration.py -v
```

### Authentication Testing
```bash
# Mock authentication (LocalStack free tier)
# Use test accounts: admin@example.com / admin123, test@example.com / test123

# Real Cognito (LocalStack paid tiers only)
make test-cognito-emails  # Only works with paid LocalStack subscription
```

## 🌐 Web Interfaces

- **LocalStack Health**: http://localhost:4566/health
- **LocalStack Web UI**: http://localhost:4566/_localstack/health

## 📚 Documentation

- **Complete Guide**: `docs/LOCALSTACK.md`
- **Project README**: `README.md` (updated with LocalStack info)
- **Troubleshooting**: See `docs/LOCALSTACK.md`

## 🔄 Daily Workflow

### RDS Mode (Production Parity)
```bash
# Start your day with RDS emulation
make local-dev

# Test RDS connectivity
make test-rds

# Make changes to your code
# ... development work ...

# Test database operations via RDS
make test-rds-secret

# Test changes
source venv/bin/activate
export $(cat .env.localstack | xargs)
pytest tests/ -v

# End of day
make localstack-stop
```

## 🎉 Success!

Your local AWS development environment is ready with RDS emulation:

### RDS Emulation Benefits:
1. **Production parity** - Matches Aurora Serverless behavior
2. **RDS features** - Parameter groups, connection pooling, RDS APIs
3. **Secrets integration** - Database credentials via Secrets Manager
4. **Better testing** - Test RDS-specific functionality
5. **Future-proof** - Easier migration to production Aurora

### Authentication Options:
- **Free Tier**: Mock authentication with test accounts
- **Paid Tiers**: Real Cognito with full AWS functionality

Additional benefits:
- **Offline development** - No AWS account needed
- **Fast iteration** - Instant feedback without cloud latency  
- **Cost savings** - No AWS charges for development
- **Full control** - Reset and recreate resources instantly

## 🆘 Need Help?

- **Documentation**: Check `docs/LOCALSTACK.md`
- **Verification**: Run `make localstack-verify`
- **Status Check**: Run `make localstack-status`
- **Logs**: Run `make localstack-logs`

### Authentication Issues?
- **Free Tier**: Use mock accounts (admin@example.com / admin123)
- **Paid Tier**: Real Cognito should work with MailHog email testing
- **Frontend**: Check `VITE_USE_MOCK_AUTH=true` in environment

Happy coding! 🚀