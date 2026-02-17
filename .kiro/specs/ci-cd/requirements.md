# Infrastructure Modernization Requirements

## Project Overview

**Objective:** Refactor the monolithic CDK deployment into separate, independently deployable stacks with automated CI/CD pipeline.

**Current State:**
- Single monolithic stack (`TutorSystemStack-dev`) with 911 lines containing VPC, RDS, Cognito, Lambda, API Gateway, S3, CloudFront
- Manual deployment process requiring `cdk deploy` from local machine
- Frontend build requires manual script execution with hardcoded values
- No automated testing in deployment pipeline
- All infrastructure changes require full stack deployment (~5 minutes)

**Target State:**
- 6 separate CDK stacks with clear separation of concerns
- Automated CI/CD pipeline (GitHub Actions) triggered on git push
- Independent frontend/backend deployments
- Automated testing before deployment
- Infrastructure changes only deploy affected stacks

---

## Business Requirements

### BR-1: Deployment Speed
**Priority:** High  
**Description:** Reduce deployment time for common changes (frontend updates, Lambda code changes) from 5+ minutes to under 1 minute.

**Success Criteria:**
- Frontend-only changes deploy in < 30 seconds
- Backend Lambda changes deploy in < 2 minutes
- Infrastructure changes only affect relevant stacks

### BR-2: Development Velocity
**Priority:** High  
**Description:** Enable frontend and backend teams to deploy independently without blocking each other.

**Success Criteria:**
- Frontend team can deploy without backend involvement
- Backend team can deploy without frontend involvement
- No manual coordination required for deployments

### BR-3: Risk Reduction
**Priority:** High  
**Description:** Isolate deployment failures to specific components rather than entire system.

**Success Criteria:**
- Failed frontend deploy doesn't affect backend
- Failed backend deploy doesn't affect frontend
- Rollback capability for each stack independently

### BR-4: Automation
**Priority:** High  
**Description:** Eliminate manual deployment steps and human error.

**Success Criteria:**
- Zero manual steps for deployment (automated on git push)
- Automated testing before deployment
- Automated rollback on deployment failure

### BR-5: AWS Free Tier Compliance
**Priority:** Critical  
**Description:** All infrastructure must remain within AWS Free Tier limits, with any exceptions requiring explicit approval.

**Success Criteria:**
- No new AWS costs introduced by stack separation or CI/CD
- GitHub Actions usage within free tier (2,000 minutes/month)
- All resources sized for free tier (t4g.micro RDS, Lambda < 1M invocations/month, etc.)
- Cost monitoring alerts configured
- Any cost-incurring changes require explicit approval before implementation

**Free Tier Resources:**
- Lambda: 1M requests/month, 400,000 GB-seconds compute
- API Gateway: 1M requests/month (12 months)
- RDS: 750 hours/month t2.micro/t3.micro (12 months)
- S3: 5GB storage, 20,000 GET requests, 2,000 PUT requests
- CloudFront: 1TB data transfer out, 10M requests
- CloudWatch: 10 custom metrics, 10 alarms
- GitHub Actions: 2,000 minutes/month (free tier)

---

## Functional Requirements

### Stack Architecture

#### FR-1.1: Network Stack
**Description:** Isolated stack for VPC and networking resources that rarely change.

**Components:**
- VPC with 2 availability zones
- Public and private subnets
- Internet Gateway
- Route tables
- Security groups (base networking)
- VPC endpoints (S3, Secrets Manager)

**Outputs:**
- VPC ID
- Public subnet IDs
- Private subnet IDs
- Security group IDs

**Deployment Frequency:** Rarely (weeks/months)

#### FR-1.2: Database Stack
**Description:** Isolated stack for RDS and database-related resources.

**Components:**
- RDS PostgreSQL instance (db.t4g.micro - free tier eligible)
- Database security group
- Secrets Manager secret for credentials
- DB subnet group

**Dependencies:**
- Network Stack (VPC, subnets)

**Outputs:**
- Database endpoint
- Database secret ARN
- Database security group ID

**Deployment Frequency:** Rarely (weeks/months)

#### FR-1.3: Auth Stack
**Description:** Isolated stack for authentication and authorization.

**Components:**
- Cognito User Pool
- Cognito User Pool Client
- Pre-signup Lambda trigger
- Cognito-related IAM roles

**Outputs:**
- User Pool ID
- User Pool Client ID
- User Pool ARN

**Deployment Frequency:** Occasionally (weeks)

#### FR-1.4: Backend Stack
**Description:** Stack for Lambda functions and API Gateway that change frequently.

**Components:**
- All Lambda functions (Quiz Engine, Answer Evaluator, DB Proxy, Auth, User Profile, Domain Management, Progress Tracking)
- Lambda layers
- API Gateway REST API
- API Gateway Cognito authorizer
- Lambda IAM roles and policies
- CloudWatch log groups

**Dependencies:**
- Network Stack (VPC, security groups)
- Database Stack (RDS endpoint, credentials)
- Auth Stack (Cognito User Pool)

**Outputs:**
- API Gateway URL
- Lambda function ARNs
- Lambda function names

**Deployment Frequency:** Daily/multiple times per day

#### FR-1.5: Frontend Stack
**Description:** Stack for static website hosting that changes frequently.

**Components:**
- S3 bucket for static hosting
- CloudFront distribution
- CloudFront Origin Access Identity
- S3 bucket deployment (from dist/)

**Dependencies:**
- Backend Stack (API Gateway URL for config)
- Auth Stack (Cognito IDs for config)

**Outputs:**
- CloudFront URL
- S3 bucket name
- CloudFront distribution ID

**Deployment Frequency:** Daily/multiple times per day

#### FR-1.6: Monitoring Stack
**Description:** Stack for observability and cost tracking.

**Components:**
- CloudWatch dashboards
- CloudWatch alarms
- SNS topics for alerts
- AWS Budgets
- Cost anomaly detection

**Dependencies:**
- Backend Stack (Lambda function names)
- Frontend Stack (CloudFront distribution ID)

**Outputs:**
- Dashboard URL
- SNS topic ARNs
- Budget limits

**Deployment Frequency:** Occasionally (weeks)

---

### CI/CD Pipeline

#### FR-2.1: Automated Build and Test
**Description:** Automatically build and test code on every push to main branch.

**Requirements:**
- Trigger on push to main branch
- Run backend unit tests
- Run frontend unit tests
- Run CDK synth to validate infrastructure code
- Fail pipeline if any tests fail

#### FR-2.2: Automated Deployment
**Description:** Automatically deploy to AWS after successful build and test.

**Requirements:**
- Deploy stacks in correct dependency order
- Only deploy stacks that have changes
- Provide deployment status notifications
- Store deployment artifacts

**Deployment Order:**
1. Network Stack (if changed)
2. Database Stack (if changed)
3. Auth Stack (if changed)
4. Backend Stack (if changed)
5. Frontend Stack (if changed)
6. Monitoring Stack (if changed)

#### FR-2.3: Environment Management
**Description:** Support multiple deployment environments (dev, staging, prod).

**Requirements:**
- Separate AWS accounts or isolated stacks per environment
- Environment-specific configuration
- Promote deployments from dev → staging → prod
- Manual approval gate for production deployments

#### FR-2.4: Rollback Capability
**Description:** Ability to quickly rollback failed deployments.

**Requirements:**
- Automatic rollback on deployment failure
- Manual rollback capability via GitHub Actions
- Preserve previous stack versions
- Rollback time < 5 minutes

#### FR-2.5: Deployment Notifications
**Description:** Notify team of deployment status.

**Requirements:**
- Slack/email notification on deployment start
- Slack/email notification on deployment success
- Slack/email notification on deployment failure
- Include deployment details (commit, stacks deployed, duration)

---

### Frontend Build Process

#### FR-3.1: Dynamic Configuration
**Description:** Frontend build process should automatically fetch configuration from deployed backend.

**Requirements:**
- Read Cognito User Pool ID from CDK outputs
- Read Cognito Client ID from CDK outputs
- Read API Gateway URL from CDK outputs
- Generate frontend config file with these values
- No hardcoded values in build script

#### FR-3.2: Build Optimization
**Description:** Optimize frontend build for production deployment.

**Requirements:**
- Minification and tree-shaking
- Asset compression (gzip/brotli)
- Cache busting with content hashes
- Source maps for debugging
- Bundle size < 250KB gzipped

#### FR-3.3: CloudFront Cache Invalidation
**Description:** Automatically invalidate CloudFront cache after frontend deployment.

**Requirements:**
- Invalidate all paths (/*) after deployment
- Wait for invalidation to complete before marking deployment successful
- Handle invalidation failures gracefully

---

## Non-Functional Requirements

### NFR-1: Performance
- Stack deployment time < 5 minutes per stack
- Frontend deployment time < 30 seconds
- Backend deployment time < 2 minutes
- Pipeline execution time < 10 minutes total

### NFR-2: Reliability
- Pipeline success rate > 95%
- Automatic retry on transient failures
- Rollback on deployment failure
- No data loss during deployments

### NFR-3: Security
- AWS credentials stored as GitHub Secrets
- No secrets in code or logs
- Least-privilege IAM roles for GitHub Actions
- Audit trail of all deployments

### NFR-4: Observability
- CloudWatch logs for all pipeline executions
- Deployment metrics tracked in CloudWatch
- Cost tracking per stack
- Alert on deployment failures

### NFR-5: Maintainability
- Clear documentation for pipeline configuration
- Reusable GitHub Actions workflows
- Infrastructure code follows CDK best practices
- Consistent naming conventions across stacks

---

## Migration Requirements

### MR-1: Simple Migration Strategy
**Description:** Migrate from monolithic stack to multi-stack architecture with planned downtime.

**Strategy:**
1. Schedule maintenance window (communicate to users)
2. Delete existing monolithic stack (`TutorSystemStack-dev`)
3. Deploy new separate stacks in dependency order
4. Verify all functionality works
5. Resume service

**Estimated Downtime:** 15-30 minutes

### MR-2: Data Preservation
**Description:** Ensure no data loss during migration.

**Requirements:**
- Export/backup RDS database before deletion
- Export Cognito User Pool users (if needed)
- Backup S3 frontend bucket contents
- Preserve CloudWatch logs (export if needed)
- Restore data to new stacks after deployment

### MR-3: Rollback Plan
**Description:** Ability to rollback to monolithic stack if migration fails.

**Requirements:**
- Keep monolithic stack code in git (tagged)
- Document rollback procedure
- Have database backup ready to restore
- Rollback time < 30 minutes

---

## Success Metrics

### Deployment Metrics
- **Deployment Frequency:** Increase from 1-2/week to 5-10/day
- **Deployment Duration:** Reduce from 5+ minutes to < 2 minutes average
- **Deployment Failure Rate:** < 5%
- **Mean Time to Recovery:** < 10 minutes

### Development Metrics
- **Time to Production:** Reduce from hours (manual) to minutes (automated)
- **Developer Productivity:** Reduce deployment overhead from 30 min/day to 0
- **Deployment Confidence:** Increase from 60% to 95% (via automated testing)

### Cost Metrics
- **Infrastructure Cost:** No increase (same resources, different organization)
- **Developer Time Saved:** 2-3 hours/week per developer
- **Incident Response Time:** Reduce from 1 hour to 15 minutes

---

## Out of Scope

The following are explicitly **not** included in this project:

- ❌ New features or functionality
- ❌ Database schema changes
- ❌ UI/UX improvements
- ❌ Performance optimization of existing code
- ❌ Multi-region deployment
- ❌ Blue-green deployment strategy (future enhancement)
- ❌ Canary deployments (future enhancement)

---

## Dependencies

### External Dependencies
- GitHub (source control and CI/CD platform)
- AWS Account with appropriate permissions
- AWS CDK CLI (v2.x)
- Node.js (for CDK and frontend build)
- Python 3.12+ (for CDK stacks)

### Internal Dependencies
- Existing monolithic stack must remain functional during migration
- Quiz engine deployment (Phases 1-6) must be complete
- No active development on infrastructure during migration window

---

## Risks and Mitigations

### Risk 1: Resource Name Conflicts
**Risk:** New stacks may conflict with existing monolithic stack resource names.  
**Mitigation:** Use different stack names and logical IDs. Test in isolated AWS account first.

### Risk 2: Cross-Stack Reference Issues
**Risk:** Circular dependencies between stacks could block deployment.  
**Mitigation:** Carefully design stack dependencies. Use SSM Parameter Store for loose coupling if needed.

### Risk 3: CloudFormation Limits
**Risk:** AWS CloudFormation has limits on stack size and resources.  
**Mitigation:** Monitor stack sizes. Split large stacks if approaching limits.

### Risk 4: Deployment Pipeline Failures
**Risk:** GitHub Actions outage could block deployments.  
**Mitigation:** Maintain ability to deploy manually via CDK CLI. Document manual deployment procedure.

### Risk 5: Migration Complexity
**Risk:** Migration from monolithic to multi-stack could introduce bugs.  
**Mitigation:** Migrate one stack at a time. Comprehensive testing after each step. Maintain rollback capability.

---

## Timeline Estimate

**Total Duration:** 2-3 weeks

### Week 1: Stack Separation
- Days 1-2: Create Network Stack and Database Stack
- Days 3-4: Create Auth Stack and Backend Stack
- Day 5: Create Frontend Stack and Monitoring Stack

### Week 2: CI/CD Pipeline
- Days 1-2: Set up GitHub Actions workflow
- Days 3-4: Implement automated testing and deployment
- Day 5: Add notifications and monitoring

### Week 3: Migration and Validation
- Days 1-2: Migrate from monolithic to multi-stack (dev environment)
- Days 3-4: Testing and validation
- Day 5: Documentation and knowledge transfer

---

## References

- [AWS CDK Best Practices](https://docs.aws.amazon.com/cdk/v2/guide/best-practices.html)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS CloudFormation Stack Dependencies](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-attribute-dependson.html)
- Current monolithic stack: `infrastructure/stacks/tutor_system_stack.py`
- Quiz engine deployment spec: `.kiro/specs/quiz-engine-deployment/`
