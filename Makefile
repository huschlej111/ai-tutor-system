# Makefile for Know-It-All Tutor System

.PHONY: help setup install test lint format clean deploy bootstrap security security-install localstack-start localstack-stop localstack-setup localstack-status local-dev

# Default target
help:
	@echo "Available targets:"
	@echo "  setup      - Set up development environment"
	@echo "  install    - Install dependencies"
	@echo "  test       - Run tests"
	@echo "  lint       - Run linting"
	@echo "  format     - Format code"
	@echo "  clean      - Clean build artifacts"
	@echo "  bootstrap  - Bootstrap CDK"
	@echo "  deploy     - Deploy to development"
	@echo "  deploy-prod - Deploy to production"
	@echo "  security   - Run all security scans"
	@echo "  security-install - Install security tools"
	@echo ""
	@echo "LocalStack targets:"
	@echo "  localstack-start  - Start LocalStack (uses existing PostgreSQL)"
	@echo "  localstack-stop   - Stop LocalStack"
	@echo "  localstack-setup  - Initialize LocalStack resources"
	@echo "  localstack-setup-rds - Setup RDS instance (Aurora Serverless-like)"
	@echo "  localstack-status - Check LocalStack status"
	@echo "  localstack-verify - Verify complete setup"
	@echo "  database-setup    - Setup PostgreSQL database"
	@echo "  local-dev        - Start local development with RDS emulation"
	@echo "  test-rds         - Test RDS connectivity"
	@echo "  test-rds-secret  - Test RDS credentials from Secrets Manager"
	@echo "  test-rotation     - Test key rotation policies"
	@echo "  configure-rotation - Configure rotation policies"
	@echo "  test-cognito-emails - Test Cognito email functionality with MailHog"

# Set up development environment
setup:
	python scripts/setup_environment.py

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -r src/lambda_functions/requirements.txt
	pip install -r infrastructure/requirements.txt
	pip install -e .

# Run tests
test:
	pytest tests/ -v

# Run property-based tests with proper environment setup
test-properties:
	python scripts/run_property_tests.py

# Run specific property-based test
test-property:
	python scripts/run_property_tests.py --test $(TEST)

# Run linting
lint:
	flake8 src/ infrastructure/ scripts/
	mypy src/ --ignore-missing-imports

# Format code
format:
	black src/ infrastructure/ scripts/
	isort src/ infrastructure/ scripts/

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/
	rm -rf cdk.out/

# Bootstrap CDK
bootstrap:
	cdk bootstrap --context environment=development

# Deploy to development
deploy:
	python scripts/deploy.py --environment development --auto-approve

# Deploy to production
deploy-prod:
	python scripts/deploy.py --environment production

# Run local development server (placeholder)
dev:
	@echo "Local development server not implemented yet"
	@echo "Use 'make deploy' to deploy to development environment"

# LocalStack targets
localstack-start:
	@echo "Starting LocalStack (using existing PostgreSQL)..."
	docker-compose -f docker-compose.localstack.yml up -d localstack
	@echo "Waiting for LocalStack to be ready..."
	@sleep 10
	@echo "LocalStack started at http://localhost:4566"
	@echo "Using existing PostgreSQL at localhost:5432"

localstack-stop:
	@echo "Stopping LocalStack..."
	docker-compose -f docker-compose.localstack.yml down

localstack-setup:
	@echo "Setting up LocalStack resources..."
	bash -c "source venv/bin/activate && python3 scripts/localstack_setup.py"

localstack-setup-rds:
	@echo "Setting up LocalStack RDS (Aurora Serverless emulation)..."
	bash -c "source venv/bin/activate && python3 scripts/setup_rds_localstack.py"

localstack-status:
	@echo "Checking LocalStack status..."
	@echo ""
	@echo "🏥 LocalStack Health:"
	@curl -s http://localhost:4566/health | python3 -m json.tool 2>/dev/null || echo "❌ LocalStack not running"
	@echo ""
	@echo "🐳 Docker Containers:"
	@docker-compose -f docker-compose.localstack.yml ps --format "table {{.Name}}\t{{.State}}\t{{.Ports}}" 2>/dev/null || echo "❌ Docker containers not found"
	@echo ""
	@echo "🌐 Service Endpoints:"
	@echo "  LocalStack Gateway: http://localhost:4566"
	@echo "  LocalStack Health:  http://localhost:4566/health"
	@echo "  MailHog Web UI:     http://localhost:8025"
	@echo "  PostgreSQL:         localhost:5432"

localstack-logs:
	docker-compose -f docker-compose.localstack.yml logs -f localstack

database-setup:
	@echo "Setting up local PostgreSQL database..."
	python3 scripts/setup_local_database.py

local-dev: database-setup localstack-start localstack-setup-rds
	@echo "🚀 Local development environment with RDS emulation is ready!"
	@echo ""
	@echo "Services available:"
	@echo "  - LocalStack: http://localhost:4566"
	@echo "  - PostgreSQL: via LocalStack RDS (Aurora Serverless emulation)"
	@echo "  - RDS Endpoint: localhost:4566"
	@echo "  - Health check: http://localhost:4566/health"
	@echo ""
	@echo "Environment variables loaded from .env.localstack"
	@echo "Use 'make localstack-stop' to stop LocalStack"

# Deploy CDK stack to LocalStack with environment-aware authentication
deploy-local-cdk:
	@echo "🚀 Deploying CDK stack to LocalStack with environment-aware authentication..."
	@echo "Setting up LocalStack environment..."
	@export $(cat .env.localstack | xargs) && \
	export CDK_DEFAULT_ACCOUNT=000000000000 && \
	export CDK_DEFAULT_REGION=us-east-1 && \
	export CDK_DISABLE_LEGACY_EXPORT_WARNING=1 && \
	npx cdklocal bootstrap aws://000000000000/us-east-1 && \
	npx cdklocal deploy TutorSystemStack-development \
		--context environment=development \
		--context account=000000000000 \
		--context region=us-east-1 \
		--require-approval never \
		--outputs-file cdk-outputs-local.json
	@echo "✅ LocalStack CDK deployment completed!"
	@echo ""
	@echo "🔧 Environment Configuration:"
	@echo "   Stage: development (no Cognito authorizer)"
	@echo "   Authentication: JWT token decode without signature verification"
	@echo "   API Gateway: All endpoints accessible without authorization"
	@echo ""
	@echo "📋 Next Steps:"
	@echo "   1. Frontend will use real Cognito for authentication"
	@echo "   2. Backend will decode JWT tokens locally for development"
	@echo "   3. Use 'make deploy-prod' for production deployment with full authorization"

# Deploy CDK stack to production AWS with full authorization
deploy-prod-cdk:
	@echo "🚀 Deploying CDK stack to production AWS..."
	cdk bootstrap
	cdk deploy TutorSystemStack-prod \
		--parameters Stage=prod \
		--require-approval never \
		--outputs-file cdk-outputs-prod.json
	@echo "✅ Production deployment completed!"
	@echo ""
	@echo "🔧 Environment Configuration:"
	@echo "   Stage: prod (Cognito User Pool Authorizer enabled)"
	@echo "   Authentication: Full Cognito authorization on all protected endpoints"
	@echo "   API Gateway: Cognito authorizer validates all requests"

# Test environment-aware authentication
test-auth-local:
	@echo "🧪 Testing local environment authentication..."
	@python3 test_environment_aware_auth.py

test-auth-integration:
	@echo "🧪 Testing authentication integration with backend..."
	@curl -X GET http://localhost:4566/restapis/*/local/_user_request_/auth/validate \
		-H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZ2l2ZW5fbmFtZSI6IlRlc3QiLCJmYW1pbHlfbmFtZSI6IlVzZXIiLCJjb2duaXRvOmdyb3VwcyI6WyJzdHVkZW50Il0sImVtYWlsX3ZlcmlmaWVkIjp0cnVlfQ.dummy-signature" \
		-H "Content-Type: application/json" | python3 -m json.tool

local-test:
	@echo "Running tests against LocalStack..."
	@export $(cat .env.localstack | xargs) && pytest tests/ -v -m "not slow"

test-rds:
	@echo "Testing RDS connection through LocalStack..."
	@export $(cat .env.localstack.rds | xargs) && python3 -c "
	import boto3
	import json
	rds = boto3.client('rds', endpoint_url='http://localhost:4566', aws_access_key_id='test', aws_secret_access_key='test', region_name='us-east-1')
	try:
    	instances = rds.describe_db_instances()
    	print('✅ RDS instances:', [db['DBInstanceIdentifier'] for db in instances['DBInstances']])
	except Exception as e:
    	print('❌ RDS connection failed:', e)
	"

test-rds-secret:
	@echo "Testing RDS credentials from Secrets Manager..."
	@export $(cat .env.localstack.rds | xargs) && python3 -c "
	import boto3
	import json
	sm = boto3.client('secretsmanager', endpoint_url='http://localhost:4566', aws_access_key_id='test', aws_secret_access_key='test', region_name='us-east-1')
	try:
		secret = sm.get_secret_value(SecretId='tutor-system/database/credentials')
		creds = json.loads(secret['SecretString'])
		print('✅ Database credentials retrieved:')
		print(f\"  Host: {creds['host']}\")
		print(f\"  Database: {creds['dbname']}\")
		print(f\"  Username: {creds['username']}\")
	except Exception as e:
		print('❌ Secret retrieval failed:', e)
	"

test-lambda-secrets:
	@echo "Testing Lambda function with Secrets Manager..."
	bash -c "source venv/bin/activate && python3 src/lambda_functions/example_secrets_usage/handler.py"

localstack-verify:
	@echo "Verifying LocalStack setup..."
	@bash -c "set -a; source .env.localstack; set +a; source venv/bin/activate && python3 scripts/verify_localstack.py"

# Package Lambda functions
package:
	@echo "Packaging Lambda functions..."
	cd src/lambda_functions && zip -r ../../lambda_functions.zip . -x "*.pyc" "*/__pycache__/*"

# Validate CDK templates
validate:
	cdk synth --context environment=development > /dev/null
	@echo "CDK templates are valid"

# Show CDK diff
diff:
	cdk diff --context environment=development

# Destroy infrastructure (development only)
destroy:
	cdk destroy --context environment=development --force

# Security scanning
security-install:
	pip install bandit checkov pip-audit
	@echo "Note: TruffleHog must be installed separately from https://github.com/trufflesecurity/trufflehog"

security:
	python scripts/security_scan.py --fail-on-issues

security-bandit:
	python scripts/security_scan.py --tool bandit

security-checkov:
	python scripts/security_scan.py --tool checkov

security-secrets:
	python scripts/security_scan.py --tool trufflehog

security-deps:
	python scripts/security_scan.py --tool pip-audit

# Security monitoring setup
security-monitoring-setup:
	python scripts/setup_security_monitoring.py --environment $(or $(ENV),development)

security-monitoring-validate:
	python scripts/setup_security_monitoring.py --validate-only --environment $(or $(ENV),development)

# Secrets management setup
secrets-setup:
	python scripts/setup_secrets_management.py --environment $(or $(ENV),development)

secrets-validate:
	python scripts/setup_secrets_management.py --validate-only --environment $(or $(ENV),development)

secrets-test:
	python scripts/setup_secrets_management.py --test-access --environment $(or $(ENV),development)

# Key rotation policy testing
test-rotation:
	@echo "Testing key rotation policies..."
	python3 scripts/test_rotation_policy.py --localstack

test-rotation-aws:
	@echo "Testing AWS key rotation policies..."
	python3 scripts/test_rotation_policy.py --aws

configure-rotation:
	@echo "Configuring rotation policies..."
	python3 scripts/test_rotation_policy.py --configure

# Cognito email testing
test-cognito-emails:
	@echo "Testing Cognito email functionality with MailHog..."
	python3 scripts/test_cognito_emails.py

mailhog-ui:
	@echo "Opening MailHog web interface..."
	@command -v open >/dev/null 2>&1 && open http://localhost:8025 || echo "Visit http://localhost:8025 in your browser"