# GitHub Actions Setup

## Required GitHub Secrets

Before the CI/CD pipeline can run, you need to add AWS credentials to GitHub Secrets:

1. Go to: https://github.com/huschlej111/ai-tutor-system/settings/secrets/actions

2. Add the following secrets:
   - `AWS_ACCESS_KEY_ID` - Your AWS access key
   - `AWS_SECRET_ACCESS_KEY` - Your AWS secret key

## Getting AWS Credentials

If you don't have programmatic access keys:

```bash
# Check current credentials
aws sts get-caller-identity

# If using IAM user, create access keys in AWS Console:
# https://console.aws.amazon.com/iam/home#/users
# Select your user → Security credentials → Create access key
```

## Testing the Workflow

Once secrets are added:

```bash
# Commit and push the workflow
git add .github/workflows/deploy.yml
git commit -m "Add CI/CD pipeline"
git push

# The workflow will trigger automatically on push to main
# Or trigger manually: https://github.com/huschlej111/ai-tutor-system/actions
```

## Workflow Overview

The pipeline deploys stacks in this order:
1. **Validate** - CDK synth check
2. **Network** - VPC, security groups
3. **Database** - RDS (parallel with Auth)
4. **Auth** - Cognito (parallel with Database)
5. **Backend** - Lambda functions, API Gateway
6. **Frontend** - S3, CloudFront
7. **Monitoring** - CloudWatch dashboard, alarms

## Estimated Duration

- First run: ~15 minutes (includes Docker builds)
- Subsequent runs: ~5-10 minutes (cached assets)
- Frontend-only changes: ~2 minutes
