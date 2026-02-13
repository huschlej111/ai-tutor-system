# Unit Test Restructuring Plan

## Summary
Restructure unit tests to remove LocalStack and database dependencies by using mocks instead.

## Changes Made

### 1. conftest.py ✅
- Removed all LocalStack setup fixtures
- Removed database connection fixtures  
- Added mock fixtures: `mock_db_connection`, `mock_db_cursor`, `mock_cognito`, `test_user`
- Changed markers from `localstack` to `unit` and `integration`

### 2. test_answer_evaluation_unit.py ✅
- Removed `test_environment` parameter from all tests
- Added `@pytest.mark.unit` decorator
- Tests already use proper mocking - no database calls

## Remaining Work

### 3. test_auth_unit.py
**Status**: Partially done (already uses moto)
**Changes needed**:
- Remove `test_environment` fixture dependency
- Ensure all AWS calls use moto mocking
- Add `@pytest.mark.unit` decorator

### 4. test_batch_upload_unit.py  
**Status**: Needs major refactoring
**Current issues**:
- Has `@pytest.mark.localstack` on 9 tests
- Calls `get_db_connection()` directly
- Creates real test users in database
**Changes needed**:
- Replace `@pytest.mark.localstack` with `@pytest.mark.unit`
- Mock `get_db_connection` and database operations
- Remove `create_test_user()` and `cleanup_test_user()` functions
- Use `mock_db_connection` fixture instead
- Mock cursor.execute() and cursor.fetchone() responses

### 5. test_domain_unit.py
**Status**: Needs refactoring
**Current issues**:
- Uses `test_environment` and `clean_database` fixtures
- May have database calls
**Changes needed**:
- Remove fixture dependencies
- Add `@pytest.mark.unit` decorator
- Mock any database operations

### 6. test_progress_unit.py
**Status**: Needs refactoring  
**Current issues**:
- Uses database fixtures
- Direct database calls
**Changes needed**:
- Remove fixture dependencies
- Add `@pytest.mark.unit` decorator
- Mock database operations

### 7. test_quiz_unit.py
**Status**: Needs major refactoring
**Current issues**:
- Has `@pytest.mark.localstack` on 6 tests
- Calls `get_db_connection()` directly
- Creates domains and terms in database
**Changes needed**:
- Replace `@pytest.mark.localstack` with `@pytest.mark.unit`
- Mock all database operations
- Remove `create_test_user()` and `create_domain_with_terms()` functions
- Use mock fixtures

## Pattern for Refactoring

### Before (with LocalStack):
```python
@pytest.mark.localstack
def test_something(test_environment, clean_database):
    user_id, email = create_test_user()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ...")
        result = cursor.fetchone()
    # test logic
```

### After (with mocks):
```python
@pytest.mark.unit
def test_something(mock_db_connection, test_user):
    mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = ('test-id', 'test@example.com')
    
    # test logic - database calls are mocked
```

## Running Unit Tests

After refactoring, run with:
```bash
pytest tests/test_*_unit.py -m unit -v
```

Or run without LocalStack/database:
```bash
pytest tests/test_*_unit.py -v
```
