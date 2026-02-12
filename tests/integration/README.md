# Integration Tests for Auth API

Tests the deployed API Gateway endpoints against live AWS infrastructure.

## Setup

Install test dependencies:
```bash
pip install pytest requests
```

## Running Tests

**Run all integration tests:**
```bash
pytest tests/integration/ -v
```

**Run specific test:**
```bash
pytest tests/integration/test_auth_api.py::TestAuthAPI::test_05_login_success -v
```

**Run with detailed output:**
```bash
pytest tests/integration/ -v -s
```

**Run only fast tests (skip slow ones):**
```bash
pytest tests/integration/ -v -m "not slow"
```

## Environment Variables

Configure the test environment:

```bash
# Test against different environment
export API_BASE_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod

# Set timeout
export API_TIMEOUT=30

# Set AWS region
export AWS_REGION=us-east-1
```

## Test Coverage

- ✅ User registration (success, duplicate, validation)
- ✅ User login (success, invalid credentials)
- ✅ Token validation (valid, invalid, missing)
- ✅ CORS headers
- ✅ Security (SQL injection, XSS attempts)
- ✅ Error handling (malformed JSON, missing body)

## CI/CD Integration

Add to GitHub Actions:
```yaml
- name: Run Integration Tests
  env:
    API_BASE_URL: ${{ secrets.API_BASE_URL }}
  run: pytest tests/integration/ -v
```

## Notes

- Tests create unique users per run (timestamp-based emails)
- Tests are idempotent and can be run multiple times
- Each test is independent and doesn't rely on others
- Tests clean up after themselves (Cognito users auto-expire in dev)
