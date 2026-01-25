# System Administrator Guide
## Know-It-All Tutor System

This guide provides comprehensive instructions for system administrators to get the Know-It-All Tutor System running locally for user acceptance testing and development.

## 🎯 Overview

The Know-It-All Tutor System is a serverless web application with the following components:
- **Frontend**: React + TypeScript + Vite (port 3000)
- **Backend**: AWS Lambda functions (via LocalStack on port 4566)
- **Database**: PostgreSQL (via LocalStack RDS emulation)
- **Authentication**: Mock authentication (Cognito requires paid LocalStack tier)
- **Email Testing**: MailHog (SMTP: 1025, Web UI: 8025) - requires paid LocalStack for Cognito
- **AWS Services**: LocalStack emulation for S3, RDS, Lambda, etc.

**Important**: The system uses mock authentication for LocalStack free tier. Real Cognito requires a paid LocalStack subscription (Base/Ultimate tier).

## 📋 Prerequisites

Before starting, ensure you have the following installed:

### Required Software
- **Python 3.11+** - For backend Lambda functions
- **Node.js 18+** - For frontend and CDK
- **PostgreSQL** - Database server
- **Docker & Docker Compose** - For LocalStack
- **Git** - Version control

### Verification Commands
```bash
# Check versions
python3 --version    # Should be 3.11+
node --version       # Should be 18+
npm --version        # Should be included with Node.js
docker --version     # Any recent version
docker-compose --version
psql --version       # PostgreSQL client

# Check PostgreSQL service
systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS
```

## 🚀 Quick Start (Recommended Path)

### 1. Initial Setup (First Time Only)
```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd know-it-all-tutor

# Complete environment setup
make setup

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Start complete local development environment
make local-dev
```

This single command (`make local-dev`) will:
- ✅ Setup PostgreSQL database and schema
- ✅ Start LocalStack with all AWS services
- ✅ Initialize S3 buckets, RDS instances, Lambda functions
- ✅ Start MailHog for email testing

### 2. Start Frontend Development Server
```bash
# In a new terminal window
cd frontend
npm install
npm run dev
```

The frontend will be available at: **http://localhost:3000**

### Verify Everything is Running
```bash
# Check all services
make localstack-status

# Test the complete setup
make localstack-verify
```

**Expected output from `make localstack-status`:**
```
Checking LocalStack status...

🏥 LocalStack Health:
{
    "services": {
        "s3": "available",
        "rds": "available",
        "lambda": "available",
        "secretsmanager": "available"
    }
}

🐳 Docker Containers:
NAME                     STATE     PORTS
tutor-system-localstack  Up        0.0.0.0:4566->4566/tcp, 4510-4559/tcp
tutor-system-mailhog     Up        0.0.0.0:1025->1025/tcp, 0.0.0.0:8025->8025/tcp

🌐 Service Endpoints:
  LocalStack Gateway: http://localhost:4566
  LocalStack Health:  http://localhost:4566/health
  MailHog Web UI:     http://localhost:8025
  PostgreSQL:         localhost:5432
```

**Expected output from `make localstack-verify`:**
```
🔍 Verifying LocalStack Setup
==================================================

📦 Docker Status:
✅ Docker is running

� Environment Variables:
✅ LOCALSTACK_ENDPOINT
✅ AWS_ACCESS_KEY_ID
✅ AWS_SECRET_ACCESS_KEY
✅ AWS_DEFAULT_REGION
✅ DATABASE_URL

🏥 LocalStack Health:
✅ LocalStack is running
   Available services:
     ✅ s3: available
     ✅ rds: available
     ✅ lambda: available
     ✅ secretsmanager: available

☁️  AWS Services:
✅ s3
✅ rds
✅ lambda
✅ secretsmanager

🗄️  Database:
✅ PostgreSQL connection

==================================================
🎉 All checks passed! LocalStack is ready for development.

Next steps:
  - Run tests: make local-test
  - Deploy CDK: cdklocal deploy
  - View LocalStack UI: http://localhost:4566/_localstack/health
```

## 🔧 Detailed Setup Instructions

### Step 1: Environment Setup

#### Create Python Virtual Environment
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Install all dependencies
make install
```

#### Configure Environment Variables
For local development, no additional configuration is needed. The system uses `.env.localstack` which contains all the necessary settings for LocalStack and Cognito authentication.

**Note**: The `.env.example` file contains legacy JWT configuration that is deprecated. The current system uses AWS Cognito for authentication, so you don't need to create a `.env` file from the example.

### Step 2: Database Setup

#### Option A: Use Existing PostgreSQL (Recommended)
```bash
# Setup database using your existing PostgreSQL installation
make database-setup
```

This creates:
- Database: `tutor_system`
- User: `tutor_user` / `tutor_password`
- Complete schema with sample data

#### Option B: Use Containerized PostgreSQL
```bash
# If you prefer Docker PostgreSQL on port 5433
docker-compose -f docker-compose.localstack-with-db.yml up -d postgres

# Update .env.localstack to use port 5433
sed -i 's/DB_PORT=5432/DB_PORT=5433/' .env.localstack
```

### Step 3: LocalStack Setup

#### Start RDS Emulation Development Environment

```bash
# Start RDS emulation development environment
make local-dev

# This provides:
# - PostgreSQL via LocalStack RDS service
# - Aurora Serverless-like behavior
# - Production parity
# - RDS features (parameter groups, etc.)
```

#### Manual Setup (Alternative)
```bash
# Start LocalStack Services
make localstack-start

# Initialize AWS resources (S3 buckets, RDS instances, etc.)
make localstack-setup-rds
```

#### Verify LocalStack is Working
```bash
# Check service health
curl http://localhost:4566/health

# List available services
make localstack-status

# Complete verification
make localstack-verify

# Test RDS connectivity
make test-rds
make test-rds-secret
```

### Step 4: Frontend Setup

#### Install and Start Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend development server will start on **http://localhost:3000**

## 🌐 Service Endpoints

Once everything is running, you'll have access to:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend App** | http://localhost:3000 | Main application interface |
| **LocalStack Gateway** | http://localhost:4566 | AWS services emulation |
| **LocalStack Health** | http://localhost:4566/health | Service status check |
| **MailHog Web UI** | http://localhost:8025 | Email testing interface |
| **PostgreSQL** | localhost:5432 | Database connection |

## 🔐 Authentication Setup for AWS Compatibility

**Important**: Since this system needs to work on real AWS infrastructure, authentication requires special consideration for local development.

### The Challenge
- LocalStack Community Edition doesn't support Cognito
- The system uses AWS Cognito for production authentication  
- Mock authentication won't work when deployed to AWS

### Solution Options

#### Option 1: Real AWS Cognito (Recommended for UAT)
Use actual AWS Cognito for local development to ensure full compatibility:

```bash
# Setup real AWS Cognito (creates actual AWS resources)
python3 scripts/setup_real_cognito.py

# This will:
# - Create a real Cognito User Pool in your AWS account
# - Create test users with known passwords
# - Update frontend configuration
# - Cost: ~$1-2 for development usage
```

**Advantages:**
- ✅ Full compatibility with production
- ✅ Real email verification works
- ✅ Identical behavior to production deployment
- ✅ Tests actual AWS integration

#### Option 2: LocalStack Pro
If you have a LocalStack Pro license:

```bash
export LOCALSTACK_API_KEY=your-pro-license-key
make localstack-stop
make localstack-start
```

#### Option 3: Skip Authentication for Core Feature Testing
For testing non-auth features (quiz engine, domain management):

```bash
# Temporarily disable authentication in frontend
# Allows testing core functionality without auth barriers
# Not suitable for full UAT
```

### Recommended Approach for UAT

For comprehensive user acceptance testing that validates AWS compatibility:

1. **Use Real AWS Cognito** (Option 1)
2. **Test complete user flows** including registration and email verification
3. **Validate production-like behavior**

### Important Notes

- **Production Ready**: The infrastructure code creates proper Cognito resources when deployed to AWS
- **Cost Consideration**: Real AWS Cognito for development costs ~$1-2/month
- **Cleanup**: Remember to delete development Cognito resources when done
- **Security**: Real Cognito provides proper security for UAT

## 🧪 Testing the System

### Basic Functionality Test
```bash
# Run integration tests
make local-test

# Test specific components
pytest tests/test_auth_unit.py -v
pytest tests/test_domain_unit.py -v
pytest tests/test_quiz_unit.py -v
```

### Email Testing with Cognito
```bash
# Test Cognito email flows
make test-cognito-emails

# View emails in MailHog
open http://localhost:8025
```

### Database Testing
```bash
# Connect to database
psql -h localhost -p 5432 -U tutor_user -d tutor_system

# Check sample data
SELECT * FROM users;
SELECT * FROM domains;
SELECT * FROM terms;
```

### API Testing
```bash
# Test Lambda functions via LocalStack
awslocal lambda list-functions
awslocal lambda invoke --function-name tutor-system-auth output.json
```

## 🔄 Daily Development Workflow

### Starting Your Development Session
```bash
# Activate Python environment
source venv/bin/activate

# Start LocalStack (if not running)
make localstack-start

# Start frontend (in separate terminal)
cd frontend && npm run dev
```

### Stopping Your Development Session
```bash
# Stop LocalStack (PostgreSQL keeps running)
make localstack-stop

# Stop frontend (Ctrl+C in terminal)
```

### Restarting After System Reboot
```bash
# Start PostgreSQL (if not auto-started)
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS

# Start development environment
make localstack-start

# Start frontend
cd frontend && npm run dev
```

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### LocalStack Won't Start
```bash
# Check Docker is running
docker ps

# Check port conflicts
lsof -i :4566  # LocalStack
lsof -i :5432  # PostgreSQL

# Restart with clean state
make localstack-stop
docker system prune -f
make local-dev
```

#### Docker Compose Container Config Error
If you see `KeyError: 'ContainerConfig'` when starting LocalStack:
```bash
# Stop all containers
make localstack-stop
docker-compose -f docker-compose.localstack.yml down

# Remove corrupted containers and images
docker container prune -f
docker image prune -f

# Remove specific LocalStack containers if they exist
docker rm -f tutor-system-localstack tutor-system-mailhog 2>/dev/null || true

# Pull fresh images
docker-compose -f docker-compose.localstack.yml pull

# Start fresh
make localstack-start
```

If the problem persists:
```bash
# Nuclear option - clean everything Docker related to this project
docker-compose -f docker-compose.localstack.yml down --volumes --remove-orphans
docker system prune -a -f --volumes

# Restart Docker service (Linux)
sudo systemctl restart docker

# Or restart Docker Desktop (macOS/Windows)
# Then try again
make localstack-start
```

#### Status Command Issues
If `make localstack-status` shows truncated output or garbled port mappings:
```bash
# Check Docker containers manually
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check LocalStack health directly
curl http://localhost:4566/health | python3 -m json.tool

# Check specific services
docker-compose -f docker-compose.localstack.yml ps
```

#### Verification Script Issues
If `make localstack-verify` shows environment variables instead of the expected output:
```bash
# Fix the environment loading
source .env.localstack
source venv/bin/activate
python3 scripts/verify_localstack.py

# Or run the verification manually
make localstack-status
curl http://localhost:4566/health
```

**Expected verification output should show:**
- ✅ Docker is running
- ✅ All environment variables are set
- ✅ LocalStack health check passes
- ✅ AWS services (S3, RDS, Lambda, Secrets Manager) are available
- ✅ PostgreSQL connection works

#### Database Connection Issues
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Test connection manually
psql -h localhost -p 5432 -U tutor_user -d tutor_system

# Reset database if needed
make database-setup
```

#### Frontend Issues
```bash
# Clear npm cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check for port conflicts
lsof -i :3000
```

#### Email Testing Issues
```bash
# Check MailHog is running
curl http://localhost:8025

# Restart LocalStack with MailHog
make localstack-stop
make localstack-start
```

### Port Conflicts Resolution

If you encounter port conflicts:

| Port | Service | Alternative |
|------|---------|-------------|
| 3000 | Frontend | Change in `frontend/vite.config.ts` |
| 4566 | LocalStack | Change in `docker-compose.localstack.yml` |
| 5432 | PostgreSQL | Use containerized version on 5433 |
| 8025 | MailHog | Change in `docker-compose.localstack.yml` |

### Performance Issues

If the system is running slowly:

```bash
# Check Docker resource usage
docker stats

# Increase Docker memory allocation (Docker Desktop)
# Recommended: 4GB RAM, 2 CPU cores

# Check available disk space
df -h

# Clean up Docker resources
docker system prune -f
```

## 📊 Monitoring and Logs

### Viewing Logs
```bash
# LocalStack logs
make localstack-logs

# Frontend logs (in terminal where npm run dev is running)

# Database logs
sudo journalctl -u postgresql -f  # Linux
tail -f /usr/local/var/log/postgres.log  # macOS
```

### Health Checks
```bash
# Complete system health check
make localstack-verify

# Individual service checks
curl http://localhost:4566/health  # LocalStack
curl http://localhost:3000         # Frontend
pg_isready -h localhost -p 5432    # PostgreSQL
curl http://localhost:8025         # MailHog
```

## 🔐 Security Considerations

### Local Development Security
- All credentials are test/development values
- LocalStack uses mock AWS credentials (`test`/`test`)
- Database uses simple credentials (`tutor_user`/`tutor_password`)
- No real AWS resources are created or charged

### Production Deployment
- Never use local development credentials in production
- Use AWS Secrets Manager for production credentials
- Enable proper IAM policies and roles
- Use HTTPS and proper SSL certificates

## 📚 Additional Resources

### Documentation
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Project README](./README.md)
- [LocalStack Setup Guide](./docs/LOCALSTACK.md)

### Useful Commands Reference
```bash
# Environment Management
make setup              # Initial setup
make local-dev         # Start everything
make localstack-start  # Start LocalStack only
make localstack-stop   # Stop LocalStack

# Testing
make local-test        # Run all tests
make test-cognito-emails  # Test email functionality
make localstack-verify    # Verify setup

# Development
source venv/bin/activate  # Activate Python env
cd frontend && npm run dev  # Start frontend

# Troubleshooting
make localstack-logs   # View LocalStack logs
make localstack-status # Check service status
docker ps              # Check running containers
```

## 🎯 User Acceptance Testing Checklist

Before conducting UAT, verify:

- [ ] All services are running (LocalStack, PostgreSQL, Frontend)
- [ ] Database contains sample data (users, domains, terms)
- [ ] Frontend loads at http://localhost:3000
- [ ] User registration/login works (check MailHog for emails)
- [ ] Quiz functionality works with sample AWS domain
- [ ] Admin features work (domain creation, batch upload)
- [ ] Email notifications appear in MailHog
- [ ] No console errors in browser developer tools

### Test User Accounts

The system includes pre-configured test accounts:

| Email | Password | Role |
|-------|----------|------|
| admin@example.com | admin123 | Administrator |
| test@example.com | test123 | Regular User |

## 🆘 Getting Help

If you encounter issues:

1. **Check this guide** - Most common issues are covered above
2. **Check logs** - Use `make localstack-logs` and browser console
3. **Verify prerequisites** - Ensure all required software is installed
4. **Clean restart** - Try `make localstack-stop && make local-dev`
5. **Contact development team** - Provide error logs and system information

---

**System Administrator Guide v1.0**  
*Last updated: January 2026*