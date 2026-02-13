# Integration Tests for Auth API

## Overview

Complete integration test suite for the Know-It-All Tutor System API. Tests run against deployed AWS infrastructure.

## Test Files

- **test_auth_api.py** - Authentication (register, login, tokens)
- **test_domain_api.py** - Domain management (CRUD operations)
- **test_quiz_api.py** - Quiz engine (sessions, questions, answers)
- **test_progress_api.py** - Progress tracking (stats, mastery)
- **test_answer_eval_api.py** - Answer evaluation (ML similarity scoring)
- **test_batch_upload_api.py** - Batch domain uploads
- **test_e2e.py** - End-to-end user journeys

## Quick Start

### 1. Install Dependencies
```bash
pip install pytest requests
```

### 2. Set API Endpoint (Optional)
```bash
export API_BASE_URL=https://o06264kkzj.execute-api.us-east-1.amazonaws.com/prod
```

### 3. Run Tests
```bash
# All tests
pytest tests/integration/ -v

# Specific test file
pytest tests/integration/test_domain_api.py -v

# With live output
pytest tests/integration/ -v -s

# Skip slow tests
pytest tests/integration/ -v -m "not slow"
```

## Test Patterns

All tests follow these patterns:
- **Unique test data** per run (timestamp-based emails)
- **Automatic cleanup** in fixtures
- **Independent tests** (no shared state)
- **Auth token management** via APITestClient

## Configuration

### Environment Variables
```bash
export API_BASE_URL=https://your-api.execute-api.region.amazonaws.com/stage
export API_TIMEOUT=30
export AWS_REGION=us-east-1
```

### AWS Credentials
Tests use your configured AWS credentials for:
- Creating/deleting test users in Cognito
- Querying CloudWatch logs for debugging

## Cost

Tests run within AWS Free Tier limits:
- ~100-500 API requests per full test run
- ~10-50 test users created (auto-expire in 30 days)
- **Estimated cost**: $0.00 (within Free Tier)

## CI/CD Integration

```yaml
# .github/workflows/integration-tests.yml
- name: Run Integration Tests
  env:
    API_BASE_URL: ${{ secrets.DEV_API_URL }}
  run: pytest tests/integration/ -v --junitxml=results.xml
```

## Documentation

- **TESTING_STRATEGY.md** - Complete testing approach
- **PROGRESS.md** - Status and next steps
