# Infrastructure Deployment Guide

## Overview

This directory contains AWS CDK infrastructure definitions for the Know-It-All Tutor system. The project uses an **iterative deployment approach** where infrastructure is built incrementally rather than all at once.

## Deployment Architecture

### Current Active Deployment (Iterative Development)

```
cdk deploy (from infrastructure/)
    ↓
infrastructure/app.py  ← ACTIVE APP
    ↓
infrastructure/stacks/auth_only_stack.py  ← ACTIVE STACK
    ↓
Creates: TutorSystemStack-dev + MonitoringStack-dev
```

**This is what you're using now for iterative development.**

### Future Full Deployment (Production-Ready)

```
scripts/deploy_to_aws.py
    ↓
infrastructure/app.py.deprecated  ← ORIGINAL MULTI-STACK DESIGN
    ↓
infrastructure/stacks/tutor_system_stack.py  ← FUTURE STACK
    ↓
Creates: Multiple stacks (Pipeline, Security, Main, Frontend, Monitoring)
```

**This will be used when transitioning to full production deployment.**

## File Structure

### Active Files (Current Workflow)

- **`app.py`** - CDK app entry point for iterative development
- **`stacks/auth_only_stack.py`** - Main stack with all infrastructure (VPC, RDS, Cognito, Lambda, API Gateway, etc.)
- **`stacks/simple_monitoring_stack.py`** - Monitoring with CloudWatch dashboard, alarms, SNS, and cost budgets
- Uses stack names: `TutorSystemStack-dev` and `MonitoringStack-dev`

### Reference Files (Not Active)

- **`app.py.deprecated`** - Original multi-stack orchestrator design (kept for reference)
- **`stacks/tutor_system_stack.py`** - Future main application stack
- **`stacks/pipeline_stack.py`** - CI/CD pipeline
- **`stacks/security_monitoring_stack.py`** - Security monitoring
- **`stacks/frontend_stack.py`** - Frontend hosting
- **`stacks/monitoring_stack.py`** - Monitoring and alerting
- **`../scripts/deploy_to_aws.py`** - Python wrapper for full deployment

## How to Deploy

### Current Iterative Deployment

**IMPORTANT:** CDK must be run from the `infrastructure/` directory for asset paths to resolve correctly.

```bash
cd infrastructure
cdk deploy --app "python app.py" --require-approval never
```

This will:
1. Use `app.py` as the entry point
2. Deploy `auth_only_stack.py` and `simple_monitoring_stack.py`
3. Create/update the `TutorSystemStack-dev` and `MonitoringStack-dev` stacks
4. Build and deploy any Docker-based Lambdas (like answer-evaluator)

**Why from infrastructure/ directory?**
The Lambda asset paths in `auth_only_stack.py` use relative paths like `../src/lambda_functions/...` which resolve correctly when CDK runs from the `infrastructure/` directory.

### First Time Setup

```bash
# Install CDK globally
npm install -g aws-cdk

# Install Python dependencies
pip install -r requirements.txt

# Bootstrap CDK (one-time per account/region)
cd infrastructure
cdk bootstrap
```

### Useful CDK Commands

```bash
# See what will change before deploying
cdk diff

# Deploy with automatic approval
cdk deploy --require-approval never

# Destroy the stack (careful!)
cdk destroy

# List all stacks
cdk list

# Synthesize CloudFormation template
cdk synth
```

## Infrastructure Components

### Current Stack (`auth_only_stack.py`)

The active stack includes:

1. **VPC** - 2 AZ, no NAT Gateway (free tier optimized)
2. **RDS PostgreSQL** - t4g.micro, 20GB (free tier)
3. **Cognito User Pool** - User authentication
4. **Lambda Functions**:
   - Pre-SignUp Trigger (auto-confirm users)
   - DB Proxy (inside VPC, database access)
   - Auth (outside VPC, Cognito access)
   - User Profile (outside VPC)
   - Domain Management (outside VPC)
   - Progress Tracking (outside VPC)
   - **Answer Evaluator (container-based, ML model)** ← Quiz Engine feature
5. **API Gateway** - REST API with Cognito authorizer
6. **S3 + CloudFront** - Frontend hosting
7. **Lambda Layer** - Shared utilities

### Lambda Bridge Pattern

The architecture uses a "Lambda Bridge" pattern:
- **Lambda A** (outside VPC) - Can access Cognito and other AWS services
- **Lambda B** (inside VPC) - Can access RDS database
- Lambda A invokes Lambda B for database operations
- No NAT Gateway needed (free tier friendly)

### Container-Based Lambdas

Some Lambdas use Docker containers instead of zip files:

- **Answer Evaluator** - Contains ML model (~2GB)
  - Built from: `../lambda/answer-evaluator/`
  - Automatically built and pushed to ECR during deployment
  - Uses CPU-only PyTorch for inference

## Adding New Infrastructure

When adding new components to `auth_only_stack.py`:

1. Add the resource definition in the appropriate section
2. Grant necessary IAM permissions
3. Add CloudFormation outputs if needed
4. Test with `cdk diff` before deploying
5. Deploy with `cdk deploy`

## Transition to Full Deployment

When ready to move to the full production architecture:

1. Migrate components from `auth_only_stack.py` to `tutor_system_stack.py`
2. Update `app.py` to use the correct stack
3. Test the full deployment in a separate environment
4. Use `scripts/deploy_to_aws.py` for automated deployment

## Troubleshooting

### Docker Build Issues

If Docker-based Lambdas fail to build:
```bash
# Check Docker is running
docker ps

# Manually build to test
cd ../lambda/answer-evaluator
docker build -t test .
```

### CDK Bootstrap Issues

If deployment fails with "stack not bootstrapped":
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Permission Issues

Ensure your AWS credentials have sufficient permissions:
- Lambda (create, update, invoke)
- ECR (create repository, push images)
- IAM (create roles, attach policies)
- VPC, RDS, Cognito, API Gateway, S3, CloudFront

## Cost Optimization

The current stack is optimized for AWS Free Tier:
- RDS: t4g.micro, 20GB, single AZ
- Lambda: Pay per invocation (generous free tier)
- No NAT Gateway ($32/month saved)
- VPC Endpoints instead of NAT for AWS services
- CloudFront: Free tier includes 1TB transfer

## Security

- All database connections encrypted
- RDS in private subnet (no public access)
- Secrets Manager for database credentials
- Cognito for user authentication
- API Gateway with Cognito authorizer
- HTTPS enforced via CloudFront

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- Project specs: `../kiro-specs/`

---

## Development History Note

During iterative development, this project originally used `app_auth_only.py` as the deployment entry point. This has been renamed to `app.py` (the standard CDK convention). The original multi-stack design from `app.py` has been preserved as `app.py.deprecated` for reference on separation of concerns patterns.
