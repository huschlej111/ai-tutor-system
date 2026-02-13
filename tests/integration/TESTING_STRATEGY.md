# Integration Testing Strategy - AWS Infrastructure

## Overview
Convert LocalStack-based integration tests to run against deployed AWS infrastructure in the `dev` environment.

## Test Structure

```
tests/
├── integration/              # AWS integration tests (live infrastructure)
│   ├── conftest.py          # Shared fixtures and configuration
│   ├── test_auth_api.py     # ✅ Already converted
│   ├── test_domain_api.py   # TODO: Domain management endpoints
│   ├── test_quiz_api.py     # TODO: Quiz engine endpoints
│   ├── test_progress_api.py # TODO: Progress tracking endpoints
│   └── test_answer_eval_api.py # TODO: Answer evaluation endpoints
└── unit/                    # Unit tests (mocked, no AWS)
    └── test_*_unit.py       # ✅ Already working
```

## Configuration

### Environment Variables
```bash
# Required
export API_BASE_URL=https://o06264kkzj.execute-api.us-east-1.amazonaws.com/prod
export AWS_REGION=us-east-1

# Optional
export API_TIMEOUT=30
export TEST_USER_PREFIX=integration_test
```

### AWS Credentials
Tests use your configured AWS credentials to:
- Create/delete test users in Cognito
- Query CloudWatch logs for debugging
- Clean up test data after runs

## Test Patterns

### 1. Authentication Flow
```python
def test_full_auth_flow(api_client):
    # Register
    user = api_client.register(email, password)
    
    # Login
    tokens = api_client.login(email, password)
    
    # Use authenticated endpoint
    response = api_client.get('/domains', auth=tokens['access_token'])
    assert response.status_code == 200
```

### 2. Resource Lifecycle
```python
def test_domain_lifecycle(api_client, auth_tokens):
    # Create
    domain = api_client.create_domain(name="Test", auth=auth_tokens)
    domain_id = domain['id']
    
    # Read
    fetched = api_client.get_domain(domain_id, auth=auth_tokens)
    assert fetched['name'] == "Test"
    
    # Update
    updated = api_client.update_domain(domain_id, name="Updated", auth=auth_tokens)
    
    # Delete
    api_client.delete_domain(domain_id, auth=auth_tokens)
```

### 3. Error Handling
```python
def test_unauthorized_access(api_client):
    response = api_client.get('/domains')  # No auth token
    assert response.status_code == 401
    
def test_invalid_input(api_client, auth_tokens):
    response = api_client.create_domain(name="", auth=auth_tokens)
    assert response.status_code == 400
```

## Test Data Management

### Isolation
- Each test run creates unique users (timestamp-based emails)
- Tests are idempotent and can run in parallel
- No shared state between tests

### Cleanup
- Test users auto-expire in dev environment (30 days)
- Optional: Cleanup script to remove old test data
- Database transactions rolled back where possible

## Running Tests

### Local Development
```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/test_domain_api.py -v

# Run with live output
pytest tests/integration/ -v -s

# Run only fast tests
pytest tests/integration/ -m "not slow"
```

### CI/CD Pipeline
```yaml
# .github/workflows/integration-tests.yml
- name: Run Integration Tests
  env:
    API_BASE_URL: ${{ secrets.DEV_API_URL }}
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  run: |
    pytest tests/integration/ -v --junitxml=integration-results.xml
```

## Cost Considerations

### AWS Free Tier Coverage
- Lambda: 1M requests/month (tests use ~100-500 per run)
- API Gateway: 1M requests/month
- Cognito: 50,000 MAUs (tests create ~10-50 users per run)
- RDS: Free tier covers test database queries

### Estimated Cost per Test Run
- **Within Free Tier**: $0.00
- **After Free Tier**: ~$0.01-0.05 per full test suite run

## Monitoring & Debugging

### CloudWatch Logs
```python
# Helper to fetch Lambda logs for failed tests
def get_lambda_logs(function_name, start_time):
    logs = boto3.client('logs')
    # Fetch logs for debugging
```

### Test Reporting
- JUnit XML for CI/CD integration
- HTML reports with pytest-html
- Coverage reports for integration coverage

## Migration Checklist

- [x] Auth API tests (already done)
- [ ] Domain Management API tests
- [ ] Quiz Engine API tests
- [ ] Progress Tracking API tests
- [ ] Answer Evaluation API tests
- [ ] Batch Upload API tests
- [ ] End-to-end user journey tests
- [ ] Performance/load tests (optional)

## Next Steps

1. Create `test_domain_api.py` following auth pattern
2. Create shared `APITestClient` helper class
3. Add cleanup utilities for test data
4. Document environment setup in main README
5. Add to CI/CD pipeline
