"""
Pytest configuration and fixtures for Know-It-All Tutor System tests
Unit tests use mocking, integration tests use LocalStack
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set test environment variables BEFORE any imports
os.environ.setdefault('USER_POOL_ID', 'us-east-1_test123456')
os.environ.setdefault('USER_POOL_CLIENT_ID', 'test-client-id-123456')
os.environ.setdefault('AWS_REGION', 'us-east-1')
os.environ.setdefault('ENVIRONMENT', 'test')

# Add src directories to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "shared"))
sys.path.insert(0, str(project_root / "src" / "lambda_functions"))
sys.path.insert(0, str(project_root / "src"))


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests (use mocking)")
    config.addinivalue_line("markers", "integration: Integration tests (require LocalStack)")
    config.addinivalue_line("markers", "slow: Slow running tests")


@pytest.fixture
def mock_db_connection():
    """Mock database connection for unit tests"""
    with patch('shared.database.get_db_connection') as mock_conn:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value = mock_cursor
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.__exit__.return_value = None
        mock_conn.return_value = mock_connection
        yield mock_connection, mock_cursor


@pytest.fixture
def mock_db_cursor():
    """Mock database cursor for unit tests"""
    with patch('shared.database.get_db_cursor') as mock:
        cursor = MagicMock()
        mock.return_value.__enter__.return_value = cursor
        yield cursor


@pytest.fixture
def test_user():
    """Provide test user data"""
    return {
        'id': 'test-user-123',
        'email': 'test@example.com',
        'cognito_sub': 'test-cognito-sub-123'
    }


@pytest.fixture
def mock_cognito():
    """Mock Cognito client for unit tests"""
    with patch('boto3.client') as mock_client:
        cognito_mock = MagicMock()
        mock_client.return_value = cognito_mock
        yield cognito_mock
