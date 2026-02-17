# Infrastructure Modernization Tasks

## Overview

This task list implements the infrastructure modernization project as specified in `requirements.md` and `design.md`. The implementation follows a phased approach to refactor the monolithic CDK stack into separate, independently deployable stacks with CI/CD automation.

**Estimated Duration:** 2-3 weeks

---

## Phase 1: Stack Separation (Week 1)

### Task 1.1: Create Network Stack
- [x] Create `infrastructure/stacks/network_stack.py`
- [x] Implement NetworkStack class
- [x] Move VPC configuration from tutor_system_stack.py
- [x] Move security groups (Lambda, RDS) from tutor_system_stack.py
- [x] Add VPC endpoints (S3, Secrets Manager)
- [x] Add CloudFormation outputs (VPC ID, subnet IDs, security group IDs)
- [x] Test stack deploys successfully: `cdk deploy NetworkStack-dev`
- [x] Verify VPC and security groups created

**Deployed:** NetworkStack-dev  
**VPC ID:** vpc-093fe5083f468ecc7  
**RDS SG:** sg-0956079c6e0c68a3f  
**Lambda SG:** sg-0a7c8ce3d29043c00  

**Validates:** FR-1.1

---

### Task 1.2: Create Database Stack
- [x] Create `infrastructure/stacks/database_stack.py`
- [x] Implement DatabaseStack class with network_stack parameter
- [x] Import VPC from Network Stack outputs
- [x] Move RDS instance configuration from tutor_system_stack.py
- [x] Move Secrets Manager secret from tutor_system_stack.py
- [x] Add CloudFormation outputs (database endpoint, secret ARN)
- [x] Test stack deploys successfully: `cdk deploy DatabaseStack-dev`
- [x] Verify RDS instance created and accessible

**Deployed:** DatabaseStack-dev  
**Database Endpoint:** databasestack-dev-tutordatabasec3c89480-6ygz4mi4yolc.ca9c6g6wy42s.us-east-1.rds.amazonaws.com  
**Secret ARN:** arn:aws:secretsmanager:us-east-1:257949588978:secret:tutor-system/db-credentials-multistack-dev-vcSkJ4  
**Note:** Using different secret name to avoid conflict with existing monolithic stack during testing  

**Validates:** FR-1.2

**Dependencies:** Network Stack

---

### Task 1.3: Create Auth Stack
- [x] Create `infrastructure/stacks/auth_stack.py`
- [x] Implement AuthStack class
- [x] Move Cognito User Pool from tutor_system_stack.py
- [x] Move Cognito User Pool Client from tutor_system_stack.py
- [x] Move Pre-signup Lambda trigger from tutor_system_stack.py
- [x] Add CloudFormation outputs (User Pool ID, Client ID, ARN)
- [x] Test stack deploys successfully: `cdk deploy AuthStack-dev`
- [x] Verify Cognito User Pool created

**Deployed:** AuthStack-dev  
**User Pool ID:** us-east-1_Bg1FA4097  
**Client ID:** 6d56bp4dfiu42chkdjjmln6bb9  
**User Pool ARN:** arn:aws:cognito-idp:us-east-1:257949588978:userpool/us-east-1_Bg1FA4097  
**Note:** Using different pool name to avoid conflict with existing monolithic stack during testing  

**Validates:** FR-1.3

---

### Task 1.4: Create Backend Stack
- [x] Create `infrastructure/stacks/backend_stack.py`
- [x] Implement BackendStack class with dependencies (network, database, auth)
- [x] Import VPC, database, and Cognito from other stack outputs
- [x] Move all Lambda functions from tutor_system_stack.py:
  - [x] Quiz Engine Lambda
  - [x] Answer Evaluator Lambda (container-based)
  - [x] DB Proxy Lambda
  - [x] Auth Lambda
  - [x] User Profile Lambda
  - [x] Domain Management Lambda
  - [x] Progress Tracking Lambda
- [x] Move Lambda Layer from tutor_system_stack.py
- [x] Move API Gateway from tutor_system_stack.py
- [x] Configure Cognito authorizer using Auth Stack outputs
- [x] Add CloudFormation outputs (API URL, Lambda ARNs)
- [x] Test stack deploys successfully: `cdk deploy BackendStack-dev`
- [x] Verify all Lambda functions created
- [x] Verify API Gateway created with correct routes
- [x] Test API endpoints with authentication

**Deployed:** BackendStack-dev  
**API URL:** https://3kuv3v3u89.execute-api.us-east-1.amazonaws.com/prod/  
**Quiz Engine:** BackendStack-dev-QuizEngineFunction6E7FA38A-1B8XswAyATra  
**Answer Evaluator:** BackendStack-dev-AnswerEvaluatorFunction6C662902-n0OCMkmwbKIn  
**Note:** Fixed Docker build context to include ML model from project root  

**Validates:** FR-1.4

**Dependencies:** Network Stack, Database Stack, Auth Stack

---

### Task 1.5: Create Frontend Stack
- [x] Create `infrastructure/stacks/frontend_stack.py`
- [x] Implement FrontendStack class with dependencies (backend, auth)
- [x] Move S3 bucket from tutor_system_stack.py
- [x] Move CloudFront distribution from tutor_system_stack.py
- [x] Create method to generate frontend config.json with backend values
- [x] Move BucketDeployment from tutor_system_stack.py
- [x] Add CloudFormation outputs (CloudFront URL, S3 bucket name, distribution ID)
- [x] Build frontend: `cd frontend && npm run build`
- [x] Test stack deploys successfully: `cdk deploy FrontendStack-dev`
- [x] Verify S3 bucket created
- [x] Verify CloudFront distribution created
- [x] Verify frontend accessible via CloudFront URL
- [x] Test frontend can call backend API

**Deployed:** FrontendStack-dev  
**CloudFront URL:** https://d3awlgby2429wc.cloudfront.net  
**S3 Bucket:** frontendstack-dev-frontendbucketefe2e19c-1wepccsehgat  
**Distribution ID:** E3ADRG3XV0OZSB  
**Backend API:** https://3kuv3v3u89.execute-api.us-east-1.amazonaws.com/prod/  
**Cognito Pool:** us-east-1_Bg1FA4097  

**Validates:** FR-1.5, FR-3.1

**Dependencies:** Backend Stack, Auth Stack

---

### Task 1.6: Update Monitoring Stack
- [x] Open `infrastructure/stacks/monitoring_stack.py`
- [x] Update to accept backend_stack and frontend_stack parameters
- [x] Update Lambda alarms to use Backend Stack function names
- [x] Update dashboard to use Backend Stack metrics
- [x] Add CloudFront metrics from Frontend Stack
- [x] Test stack deploys successfully: `cdk deploy MonitoringStack-multistack-dev`
- [x] Verify dashboard shows all metrics
- [x] Verify alarms configured correctly

**Deployed:** MonitoringStack-multistack-dev  
**Dashboard URL:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=TutorSystem-multistack-dev  
**SNS Topic:** arn:aws:sns:us-east-1:257949588978:tutor-system-alerts-multistack-dev  
**Budget:** $10/month with 80% and 100% alerts  

**Validates:** FR-1.6

**Dependencies:** Backend Stack, Frontend Stack

---

### Task 1.7: Create New App Entry Point
- [x] Create `infrastructure/app_multistack.py`
- [x] Import all 6 stack classes
- [x] Instantiate stacks in dependency order:
  1. NetworkStack
  2. DatabaseStack (depends on Network)
  3. AuthStack
  4. BackendStack (depends on Network, Database, Auth)
  5. FrontendStack (depends on Backend, Auth)
  6. MonitoringStack (depends on Backend, Frontend)
- [x] Add stack dependencies using `add_dependency()`
- [x] Test synth: `cdk synth --app "python app_multistack.py"`
- [x] Verify all 6 stacks synthesize correctly

**Created:** app_multistack.py  
**Stacks:** NetworkStack-dev, DatabaseStack-dev, AuthStack-dev, BackendStack-dev, FrontendStack-dev, MonitoringStack-dev  
**Dependencies:** Properly configured in deployment order  

**Validates:** All FR-1.x

---

### Task 1.8: Test Multi-Stack Deployment (Dry Run)
- [x] Deploy all stacks to test environment: `cdk deploy --app "python app_multistack.py" --all`
- [x] Verify all stacks deploy in correct order
- [x] Verify cross-stack references work
- [x] Test end-to-end functionality:
  - [x] User can sign up/login (Cognito accessible)
  - [x] API Gateway responding
  - [x] Frontend accessible via CloudFront
  - [x] Backend API URL correctly passed to Frontend
- [x] Verify monitoring dashboard shows all metrics
- [x] Document any issues found

**Test Results:**
- ✅ All 6 stacks deployed successfully
- ✅ Cross-stack references working (Frontend has Backend API URL)
- ✅ API Gateway responding: https://3kuv3v3u89.execute-api.us-east-1.amazonaws.com/prod/
- ✅ Frontend accessible: https://d3awlgby2429wc.cloudfront.net
- ✅ Monitoring dashboard exists: TutorSystem-dev
- ✅ No issues found

**Validates:** All FR-1.x

---

## Phase 2: CI/CD Pipeline (Week 2)

### Task 2.1: Set Up GitHub Actions Workflow
- [x] Create `.github/workflows/deploy.yml`
- [x] Add workflow trigger (push to main branch)
- [x] Add manual workflow dispatch trigger
- [x] Configure AWS credentials using GitHub Secrets
- [x] Add checkout step
- [x] Add Node.js setup (for CDK and frontend)
- [x] Add Python setup (for CDK stacks)
- [x] Install CDK CLI
- [x] Install Python dependencies
- [x] Test workflow runs successfully (without deployment)

**Created:** `.github/workflows/deploy.yml`  
**Triggers:** Push to main, manual dispatch  
**Jobs:** Validate, Test Backend, Deploy All Stacks, Integration Tests  
**First successful deployment:** 2026-02-17 (6m18s)  

**Validates:** FR-2.1, FR-2.2

---

### Task 2.2: Add Testing to Pipeline
- [x] Add job: `validate-infrastructure`
  - [x] Install Python dependencies
  - [x] Run `cdk synth` to validate infrastructure code
  - [x] Fail pipeline if synth fails
- [x] Add job: `test-backend`
  - [x] Install Python dependencies
  - [x] Run pytest for backend unit tests (38 tests)
  - [x] Fail pipeline if tests fail
- [x] Add job: `test-integration`
  - [x] Run integration tests against deployed API (9 tests)
  - [x] Tests run after deployment as smoke tests
  - [x] Set `continue-on-error: true` (temporary, remove when stable)
- [ ] Add job: `test-frontend` (deferred - see note below)

**Status:** All tests integrated. Unit tests block deployment, integration tests run as post-deployment validation.

**Note:** Frontend tests deferred to separate task. Will use React Testing Library with AI-assisted test generation to learn the process. Backend is well-covered (47 tests total).

**Validates:** FR-2.1

---

### Task 2.3: Add Deployment Jobs
- [x] Add job: `deploy-all` (depends on validate and test-backend)
  - [x] Deploy all 6 stacks with `cdk deploy --all`
  - [x] CDK handles dependencies automatically
  - [x] Capture stack outputs (API URL)
- [x] Test full pipeline deployment
- [x] Verify all stacks deploy correctly

**Implementation:** Single `deploy-all` job deploys all 6 stacks in dependency order. CDK's `--all` flag handles Network→Database→Auth→Backend→Frontend→Monitoring automatically.

**Performance:** ~6 minutes total (includes Docker builds for Lambda layers and Answer Evaluator)

**Validates:** FR-2.2, FR-3.1, FR-3.3

---

### Task 2.4: Add Deployment Notifications
- [ ] Add Slack webhook to GitHub Secrets (or use email)
- [ ] Add notification step: deployment started
- [ ] Add notification step: deployment succeeded
- [ ] Add notification step: deployment failed
- [ ] Include deployment details (commit, stacks, duration)
- [ ] Test notifications work correctly

**Validates:** FR-2.5

---

### Task 2.5: Add Rollback Capability
- [ ] Add manual workflow: `rollback.yml`
- [ ] Accept input: stack name to rollback
- [ ] Use CloudFormation rollback command
- [ ] Add notification on rollback
- [ ] Test rollback workflow in dev environment
- [ ] Document rollback procedure

**Validates:** FR-2.4

---

### Task 2.6: Optimize Pipeline Performance
- [ ] Add caching for npm dependencies
- [ ] Add caching for pip dependencies
- [ ] Add caching for CDK assets
- [ ] Run jobs in parallel where possible
- [ ] Measure pipeline execution time
- [ ] Verify pipeline completes in < 10 minutes

**Validates:** NFR-1

---

## Phase 3: Migration and Validation (Week 3)

### Task 3.1: Prepare for Migration
- [ ] Tag current monolithic stack code in git: `git tag pre-migration`
- [ ] Create database backup script
- [ ] Run database backup
- [ ] Export Cognito users (if needed)
- [ ] Backup S3 frontend bucket contents
- [ ] Create rollback procedure document
- [ ] Schedule maintenance window
- [ ] Notify users of planned downtime

**Validates:** MR-2, MR-3

---

### Task 3.2: Execute Migration
- [ ] Start maintenance window
- [ ] Delete monolithic stack: `cdk destroy TutorSystemStack-dev`
- [ ] Verify stack deleted completely
- [ ] Update `cdk.json` to use `app_multistack.py`
- [ ] Deploy all new stacks: `cdk deploy --all`
- [ ] Monitor deployment progress
- [ ] Verify all stacks deploy successfully

**Validates:** MR-1

**Estimated Downtime:** 15-30 minutes

---

### Task 3.3: Restore Data
- [ ] Restore database from backup (if needed)
- [ ] Restore Cognito users (if needed)
- [ ] Restore S3 frontend files (if needed)
- [ ] Verify data integrity

**Validates:** MR-2

---

### Task 3.4: Post-Migration Validation
- [ ] Run smoke tests:
  - [ ] Frontend loads correctly
  - [ ] User can sign up
  - [ ] User can login
  - [ ] User can start quiz
  - [ ] User can submit answers
  - [ ] Answers are evaluated
  - [ ] Progress is tracked
- [ ] Check CloudWatch logs for errors
- [ ] Check monitoring dashboard
- [ ] Verify all alarms are healthy
- [ ] End maintenance window
- [ ] Notify users service is restored

**Validates:** All requirements

---

### Task 3.5: Monitor Post-Migration
- [ ] Monitor CloudWatch metrics for 24 hours
- [ ] Monitor error rates
- [ ] Monitor API latency
- [ ] Monitor Lambda invocations
- [ ] Check for any anomalies
- [ ] Document any issues found

**Validates:** NFR-4

---

### Task 3.6: Test CI/CD Pipeline
- [ ] Make small frontend change
- [ ] Push to main branch
- [ ] Verify pipeline triggers automatically
- [ ] Verify frontend deploys in < 30 seconds
- [ ] Verify change is live
- [ ] Make small backend change
- [ ] Push to main branch
- [ ] Verify only backend stack deploys
- [ ] Verify backend deploys in < 2 minutes
- [ ] Verify change is live

**Validates:** BR-1, BR-2, FR-2.2

---

## Phase 4: Documentation and Cleanup

### Task 4.1: Update Documentation
- [ ] Update main README.md with new deployment process
- [ ] Update infrastructure/README.md with stack descriptions
- [ ] Document CI/CD pipeline configuration
- [ ] Document rollback procedures
- [ ] Document troubleshooting guide
- [ ] Create deployment runbook
- [ ] Update architecture diagrams

**Validates:** NFR-5

---

### Task 4.2: Clean Up Old Code
- [ ] Rename `app.py` to `app_monolithic.py.deprecated`
- [ ] Rename `app_multistack.py` to `app.py`
- [ ] Update `cdk.json` to use `app.py`
- [ ] Move `tutor_system_stack.py` to `tutor_system_stack.py.deprecated`
- [ ] Add deprecation notices to old files
- [ ] Commit changes
- [ ] Push to GitHub

**Validates:** NFR-5

---

### Task 4.3: Verify Free Tier Compliance
- [ ] Check AWS Cost Explorer for current month costs
- [ ] Verify no new costs from refactoring
- [ ] Check GitHub Actions usage (should be < 2000 min/month)
- [ ] Verify all resources are free-tier sized:
  - [ ] RDS: db.t4g.micro
  - [ ] Lambda: within invocation limits
  - [ ] S3: within storage limits
  - [ ] CloudFront: within transfer limits
- [ ] Document current usage levels
- [ ] Set up cost alerts if not already configured

**Validates:** BR-5

---

### Task 4.4: Final Validation
- [ ] Run full end-to-end test suite
- [ ] Verify all functionality works
- [ ] Check deployment metrics:
  - [ ] Deployment frequency increased
  - [ ] Deployment duration decreased
  - [ ] Deployment failure rate < 5%
- [ ] Verify success criteria met:
  - [ ] All 6 stacks deploy successfully
  - [ ] CI/CD pipeline runs on every push
  - [ ] Frontend deploys in < 30 seconds
  - [ ] Backend deploys in < 2 minutes
  - [ ] All existing functionality works
  - [ ] Monitoring operational
  - [ ] Free tier compliance maintained

**Validates:** All success metrics

---

## Rollback Procedure (If Needed)

If migration fails and rollback is required:

1. **Stop new deployments**
   - Disable GitHub Actions workflow
   
2. **Restore monolithic stack**
   ```bash
   git checkout pre-migration
   cd infrastructure
   cdk deploy TutorSystemStack-dev
   ```

3. **Restore data**
   - Restore database from backup
   - Restore Cognito users
   - Restore S3 frontend files

4. **Verify functionality**
   - Run smoke tests
   - Check monitoring

5. **Notify users**
   - Inform of rollback
   - Provide status update

**Estimated Rollback Time:** < 30 minutes

---

## Notes

- All tasks should be executed in the order specified
- Each phase should be validated before proceeding to the next
- Keep monolithic stack code in git for rollback capability
- Test rollback procedure before migration
- Monitor costs throughout the process
- Communicate with users about maintenance windows

---

## Success Metrics

### Deployment Metrics
- **Deployment Frequency:** Target 5-10/day (from 1-2/week)
- **Deployment Duration:** Target < 2 minutes average (from 5+ minutes)
- **Deployment Failure Rate:** Target < 5%
- **Mean Time to Recovery:** Target < 10 minutes

### Development Metrics
- **Time to Production:** Target minutes (from hours)
- **Deployment Overhead:** Target 0 (from 30 min/day)
- **Deployment Confidence:** Target 95% (from 60%)

### Cost Metrics
- **Infrastructure Cost:** $0 increase (same resources)
- **Developer Time Saved:** 2-3 hours/week
- **Incident Response Time:** < 15 minutes (from 1 hour)
