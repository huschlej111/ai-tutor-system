# Infrastructure Modernization Design

## Overview

This document describes the technical design for refactoring the monolithic CDK stack into separate, independently deployable stacks with CI/CD automation.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Frontend   │  │   Backend    │  │Infrastructure│      │
│  │     Code     │  │     Code     │  │     Code     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          │         Push to main branch         │
          └──────────────────┼──────────────────┘
                             ▼
                  ┌──────────────────────┐
                  │  GitHub Actions      │
                  │  CI/CD Pipeline      │
                  └──────────┬───────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
    ┌─────────┐        ┌─────────┐       ┌─────────┐
    │  Build  │        │  Test   │       │   CDK   │
    │         │        │         │       │  Synth  │
    └────┬────┘        └────┬────┘       └────┬────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
                  ┌──────────────────────┐
                  │   Deploy to AWS      │
                  │  (Dependency Order)  │
                  └──────────┬───────────┘
                             │
    ┌────────────────────────┼────────────────────────┐
    ▼            ▼           ▼           ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│Network │  │Database│  │  Auth  │  │Backend │  │Frontend│
│ Stack  │  │ Stack  │  │ Stack  │  │ Stack  │  │ Stack  │
└────────┘  └────────┘  └────────┘  └────────┘  └────────┘
                                                      │
                                                      ▼
                                              ┌────────────┐
                                              │Monitoring  │
                                              │  Stack     │
                                              └────────────┘
```

---

## Stack Design

### 1. Network Stack

**Purpose:** Foundation networking resources that rarely change.

**File:** `infrastructure/stacks/network_stack.py`

**Resources:**
```python
class NetworkStack(Stack):
    def __init__(self, scope, id, **kwargs):
        # VPC with 2 AZs
        self.vpc = ec2.Vpc(
            self, "TutorVPC",
            max_azs=2,
            nat_gateways=0  # Free tier optimization
        )
        
        # Security Groups
        self.lambda_sg = ec2.SecurityGroup(...)
        self.rds_sg = ec2.SecurityGroup(...)
        
        # VPC Endpoints
        self.s3_endpoint = ec2.GatewayVpcEndpoint(...)
        self.secrets_endpoint = ec2.InterfaceVpcEndpoint(...)
```

**Exports:**
- VPC ID
- Public subnet IDs
- Private subnet IDs
- Security group IDs

---

### 2. Database Stack

**Purpose:** RDS and database-related resources.

**File:** `infrastructure/stacks/database_stack.py`

**Dependencies:** Network Stack

**Resources:**
```python
class DatabaseStack(Stack):
    def __init__(self, scope, id, network_stack, **kwargs):
        # Import VPC from Network Stack
        vpc = ec2.Vpc.from_lookup(...)
        
        # RDS Instance
        self.database = rds.DatabaseInstance(
            self, "TutorDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(...),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE)
        )
        
        # Secrets Manager
        self.db_secret = secretsmanager.Secret(...)
```

**Exports:**
- Database endpoint
- Database secret ARN
- Database security group ID

---

### 3. Auth Stack

**Purpose:** Cognito authentication resources.

**File:** `infrastructure/stacks/auth_stack.py`

**Resources:**
```python
class AuthStack(Stack):
    def __init__(self, scope, id, **kwargs):
        # Cognito User Pool
        self.user_pool = cognito.UserPool(...)
        
        # User Pool Client
        self.user_pool_client = cognito.UserPoolClient(...)
        
        # Pre-signup Lambda
        self.pre_signup_lambda = _lambda.Function(...)
```

**Exports:**
- User Pool ID
- User Pool Client ID
- User Pool ARN

---

### 4. Backend Stack

**Purpose:** Lambda functions and API Gateway.

**File:** `infrastructure/stacks/backend_stack.py`

**Dependencies:** Network Stack, Database Stack, Auth Stack

**Resources:**
```python
class BackendStack(Stack):
    def __init__(self, scope, id, network_stack, database_stack, auth_stack, **kwargs):
        # Lambda Functions
        self.quiz_engine = _lambda.Function(...)
        self.answer_evaluator = _lambda.DockerImageFunction(...)
        self.db_proxy = _lambda.Function(...)
        
        # API Gateway
        self.api = apigateway.RestApi(...)
        
        # Cognito Authorizer
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self, "Authorizer",
            cognito_user_pools=[auth_stack.user_pool]
        )
```

**Exports:**
- API Gateway URL
- Lambda function ARNs

---

### 5. Frontend Stack

**Purpose:** S3 and CloudFront for static hosting.

**File:** `infrastructure/stacks/frontend_stack.py`

**Dependencies:** Backend Stack, Auth Stack

**Resources:**
```python
class FrontendStack(Stack):
    def __init__(self, scope, id, backend_stack, auth_stack, **kwargs):
        # S3 Bucket
        self.bucket = s3.Bucket(...)
        
        # CloudFront Distribution
        self.distribution = cloudfront.Distribution(...)
        
        # Generate config.json with backend values
        self._generate_config(backend_stack, auth_stack)
        
        # Deploy frontend
        s3deploy.BucketDeployment(
            self, "DeployFrontend",
            sources=[s3deploy.Source.asset("../frontend/dist")],
            destination_bucket=self.bucket,
            distribution=self.distribution
        )
```

**Exports:**
- CloudFront URL
- S3 bucket name
- Distribution ID

---

### 6. Monitoring Stack

**Purpose:** CloudWatch dashboards, alarms, budgets.

**File:** `infrastructure/stacks/monitoring_stack.py`

**Dependencies:** Backend Stack, Frontend Stack

**Resources:**
```python
class MonitoringStack(Stack):
    def __init__(self, scope, id, backend_stack, frontend_stack, **kwargs):
        # CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(...)
        
        # Lambda Alarms
        for function in backend_stack.lambda_functions:
            cloudwatch.Alarm(...)
        
        # SNS Topics
        alert_topic = sns.Topic(...)
        
        # AWS Budget
        budgets.CfnBudget(...)
```

**Exports:**
- Dashboard URL
- SNS topic ARNs

---

## CI/CD Pipeline Design

### GitHub Actions Workflow

**File:** `.github/workflows/deploy.yml`

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run backend tests
        run: pytest tests/
      - name: Run frontend tests
        run: cd frontend && npm test

  deploy-infrastructure:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
      
      - name: Deploy Network Stack
        run: cdk deploy NetworkStack-dev --require-approval never
      
      - name: Deploy Database Stack
        run: cdk deploy DatabaseStack-dev --require-approval never
      
      - name: Deploy Auth Stack
        run: cdk deploy AuthStack-dev --require-approval never
      
      - name: Deploy Backend Stack
        run: cdk deploy BackendStack-dev --require-approval never

  deploy-frontend:
    needs: deploy-infrastructure
    runs-on: ubuntu-latest
    steps:
      - name: Get stack outputs
        run: |
          API_URL=$(aws cloudformation describe-stacks ...)
          echo "VITE_API_BASE_URL=$API_URL" >> $GITHUB_ENV
      
      - name: Build frontend
        run: cd frontend && npm run build
      
      - name: Deploy Frontend Stack
        run: cdk deploy FrontendStack-dev --require-approval never
      
      - name: Invalidate CloudFront
        run: aws cloudfront create-invalidation ...

  deploy-monitoring:
    needs: [deploy-infrastructure, deploy-frontend]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy Monitoring Stack
        run: cdk deploy MonitoringStack-dev --require-approval never
```

---

## Migration Strategy

### Simple Migration with Planned Downtime

**Estimated Downtime:** 15-30 minutes

### Phase 1: Preparation

1. Tag current monolithic stack code in git for rollback
2. Backup RDS database
3. Export Cognito users (if needed)
4. Backup S3 frontend bucket
5. Schedule maintenance window and notify users

### Phase 2: Migration

1. Delete existing monolithic stack (`TutorSystemStack-dev`)
2. Deploy new stacks in dependency order:
   - NetworkStack-dev
   - DatabaseStack-dev
   - AuthStack-dev
   - BackendStack-dev
   - FrontendStack-dev
   - MonitoringStack-dev
3. Restore data to new stacks (database, users, frontend files)

### Phase 3: Validation

1. Run smoke tests
2. Verify all functionality works
3. Check monitoring dashboards
4. Resume service

### Phase 4: Cleanup

1. Remove old stack code (keep in git history)
2. Update documentation
3. Monitor for 24 hours

---

## Configuration Management

### Stack Outputs

Use CloudFormation exports for cross-stack references:

```python
# In Network Stack
CfnOutput(self, "VpcId", 
    value=self.vpc.vpc_id,
    export_name="TutorSystem-VpcId"
)

# In Database Stack
vpc_id = Fn.import_value("TutorSystem-VpcId")
```

### Environment Variables

Store environment-specific config in `cdk.json`:

```json
{
  "context": {
    "dev": {
      "account": "257949588978",
      "region": "us-east-1",
      "db_instance_type": "t4g.micro"
    },
    "prod": {
      "account": "PROD_ACCOUNT",
      "region": "us-east-1",
      "db_instance_type": "t4g.small"
    }
  }
}
```

---

## Deployment Order

**Critical:** Stacks must deploy in dependency order:

1. **Network Stack** (no dependencies)
2. **Database Stack** (depends on Network)
3. **Auth Stack** (no dependencies)
4. **Backend Stack** (depends on Network, Database, Auth)
5. **Frontend Stack** (depends on Backend, Auth)
6. **Monitoring Stack** (depends on Backend, Frontend)

---

## Rollback Strategy

### Automatic Rollback

CloudFormation automatically rolls back failed deployments.

### Manual Rollback

```bash
# Rollback specific stack
aws cloudformation rollback-stack --stack-name BackendStack-dev

# Or redeploy previous version
git checkout <previous-commit>
cdk deploy BackendStack-dev
```

---

## Cost Considerations

**No cost increase expected** - same resources, different organization.

**Potential savings:**
- Faster deployments = less developer time
- Better monitoring = catch cost issues earlier
- Independent scaling per stack

---

## Security Design

### IAM Roles

**GitHub Actions Role:**
```json
{
  "Effect": "Allow",
  "Action": [
    "cloudformation:*",
    "s3:*",
    "lambda:*",
    "apigateway:*"
  ],
  "Resource": "*"
}
```

**Least Privilege:** Each Lambda gets minimal required permissions.

### Secrets Management

- AWS credentials in GitHub Secrets
- Database credentials in Secrets Manager
- No secrets in code or logs

---

## Monitoring and Observability

### Deployment Metrics

Track in CloudWatch:
- Deployment duration
- Deployment success/failure rate
- Stack drift detection
- Resource count per stack

### Application Metrics

Existing monitoring continues:
- Lambda invocations, errors, duration
- API Gateway requests, latency
- RDS connections, CPU, storage

---

## Testing Strategy

### Pre-Deployment Tests

- Unit tests (pytest, jest)
- CDK synth validation
- Infrastructure tests (cdk-nag)

### Post-Deployment Tests

- Smoke tests (health checks)
- Integration tests
- End-to-end tests

### Rollback Tests

- Test rollback in dev environment
- Document rollback procedures
- Practice rollback scenarios

---

## Documentation Requirements

### Developer Documentation

- How to run locally
- How to deploy manually
- How to debug pipeline failures

### Operations Documentation

- Deployment runbook
- Rollback procedures
- Troubleshooting guide

### Architecture Documentation

- Stack dependency diagram
- Resource inventory
- Cost breakdown per stack

---

## Success Criteria

✅ All 6 stacks deploy successfully  
✅ CI/CD pipeline runs on every push  
✅ Frontend deploys in < 30 seconds  
✅ Backend deploys in < 2 minutes  
✅ Migration completed with planned downtime  
✅ All existing functionality works  
✅ Monitoring and alarms operational  
✅ All resources remain within AWS Free Tier  

---

## Next Steps

See `tasks.md` for detailed implementation steps.
