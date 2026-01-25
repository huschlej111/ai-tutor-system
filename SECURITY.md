# Security Policy

## Overview

The Know-It-All Tutor system implements comprehensive security measures throughout the development lifecycle, including static analysis, dependency scanning, secrets detection, and infrastructure security validation.

## Security Tools

### Static Application Security Testing (SAST)

#### Bandit
- **Purpose**: Python code security analysis
- **Configuration**: `.bandit`
- **Usage**: `make security-bandit` or `python scripts/security_scan.py --tool bandit`
- **Reports**: `security-reports/bandit-report.json`

#### Checkov
- **Purpose**: Infrastructure as Code security validation
- **Configuration**: `.checkov.yml`
- **Usage**: `make security-checkov` or `python scripts/security_scan.py --tool checkov`
- **Reports**: `security-reports/checkov-report.json`

### Secrets Detection

#### TruffleHog
- **Purpose**: Detect secrets in code and git history
- **Configuration**: `.truffleHogConfig.yml`
- **Usage**: `make security-secrets` or `python scripts/security_scan.py --tool trufflehog`
- **Reports**: `security-reports/trufflehog-report.json`

### Dependency Vulnerability Scanning

#### pip-audit
- **Purpose**: Scan Python dependencies for known vulnerabilities
- **Configuration**: `pyproject.toml` [tool.pip-audit]
- **Usage**: `make security-deps` or `python scripts/security_scan.py --tool pip-audit`
- **Reports**: `security-reports/pip-audit-report.json`

### AWS Security Monitoring

#### CloudTrail
- **Purpose**: API call logging and audit trails
- **Configuration**: Deployed via CDK SecurityMonitoringStack
- **Usage**: Automatic logging of all AWS API calls
- **Reports**: CloudWatch Logs and S3 bucket storage

#### GuardDuty
- **Purpose**: Threat detection and security monitoring
- **Configuration**: Deployed via CDK SecurityMonitoringStack
- **Usage**: Continuous monitoring with SNS alerts
- **Reports**: GuardDuty console and EventBridge integration

#### AWS Config
- **Purpose**: Compliance monitoring and configuration validation
- **Configuration**: Deployed via CDK SecurityMonitoringStack
- **Usage**: Continuous compliance checking with remediation
- **Reports**: Config console and compliance dashboards

### Secrets Management

#### AWS Secrets Manager
- **Purpose**: Secure storage and rotation of secrets
- **Configuration**: Enhanced encryption with KMS and automatic rotation
- **Usage**: `make secrets-setup` or `python scripts/setup_secrets_management.py`
- **Features**: 
  - KMS encryption with customer-managed keys
  - Automatic rotation (30 days for DB, 90 days for JWT)
  - Least privilege access policies
  - Cross-region replication support

## Running Security Scans

### Local Development

```bash
# Install security tools
make security-install

# Run all security scans
make security

# Run individual tools
make security-bandit
make security-checkov
make security-secrets
make security-deps

# Set up AWS security monitoring
make security-monitoring-setup

# Set up secrets management
make secrets-setup

# Validate configurations
make security-monitoring-validate
make secrets-validate
make secrets-test

# Using the security scanner directly
python scripts/security_scan.py --help
```

### Pre-commit Hooks

Install pre-commit hooks for automatic security checks:

```bash
pip install pre-commit
pre-commit install
```

This will run security checks on every commit, including:
- Bandit SAST scanning
- TruffleHog secrets detection
- Checkov infrastructure validation
- General security checks (private keys, AWS credentials)

### CI/CD Pipeline

Security scans run automatically on:
- Every push to main/develop branches
- Every pull request
- Daily scheduled scans at 2 AM UTC

Results are:
- Uploaded as workflow artifacts
- Posted as PR comments
- Integrated with GitHub Security tab (SARIF format)

## Security Configuration

### Bandit Configuration (`.bandit`)
- Excludes test directories
- Focuses on medium+ severity issues
- Skips false positives for test assertions
- Outputs JSON reports for CI/CD integration

### Checkov Configuration (`.checkov.yml`)
- Scans CloudFormation, Terraform, and other IaC
- Excludes non-applicable checks for serverless architecture
- Enables secrets scanning across all file types
- Fails on HIGH and CRITICAL severity issues

### TruffleHog Configuration (`.truffleHogConfig.yml`)
- Scans entire git history
- Verifies detected secrets when possible
- Excludes common false positive patterns
- Allowlists test/example data patterns

### pip-audit Configuration (`pyproject.toml`)
- Scans all installed dependencies
- Outputs detailed vulnerability descriptions
- Configurable ignore list for false positives
- JSON output for automated processing

## Security Reports

All security reports are generated in the `security-reports/` directory:

- `bandit-report.json` - SAST findings
- `checkov-report.json` - Infrastructure security issues
- `trufflehog-report.json` - Detected secrets
- `pip-audit-report.json` - Dependency vulnerabilities
- `security-summary.json` - Consolidated summary report

## Handling Security Issues

### High/Critical Severity
1. **Immediate Action Required**
2. Stop deployment if in CI/CD
3. Create security incident ticket
4. Fix within 24 hours
5. Re-run security scans to verify fix

### Medium Severity
1. **Address within 1 week**
2. Create backlog ticket
3. Plan fix in next sprint
4. Document any accepted risks

### Low Severity
1. **Address within 1 month**
2. Add to technical debt backlog
3. Consider during regular maintenance

### False Positives
1. Verify the finding is actually a false positive
2. Add to tool-specific ignore configuration
3. Document the reasoning in commit message
4. Re-run scans to verify suppression

## Security Best Practices

### Code Development
- Never commit secrets, API keys, or credentials
- Use environment variables for configuration
- Implement input validation and sanitization
- Follow secure coding guidelines
- Regular dependency updates

### Infrastructure
- Use least privilege IAM policies
- Enable encryption at rest and in transit
- Configure proper VPC security groups
- Enable AWS CloudTrail and GuardDuty
- Regular security configuration reviews

### CI/CD Pipeline
- Scan on every commit and PR
- Fail builds on high/critical issues
- Store security reports as artifacts
- Regular tool updates and configuration reviews

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please:

1. **Do NOT** create a public GitHub issue
2. Email security concerns to: [security@knowitall-tutor.com]
3. Include detailed reproduction steps
4. Allow reasonable time for response and fix
5. Follow responsible disclosure practices

## Security Contacts

- **Security Team**: security@knowitall-tutor.com
- **Development Team**: dev@knowitall-tutor.com
- **Emergency Contact**: +1-XXX-XXX-XXXX

## Compliance

This security framework helps ensure compliance with:
- OWASP Top 10 security risks
- AWS Security Best Practices
- NIST Cybersecurity Framework
- SOC 2 Type II requirements (future)

## Security Training

All developers should complete:
- OWASP Secure Coding Training
- AWS Security Fundamentals
- Company-specific security policies
- Regular security awareness updates

## Review and Updates

This security policy is reviewed:
- Quarterly by the security team
- After any security incidents
- When new tools or processes are added
- Based on threat landscape changes

Last Updated: January 2, 2025
Next Review: April 2, 2025