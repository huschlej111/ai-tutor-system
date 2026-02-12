"""
Pytest configuration for integration tests
"""
import pytest
import os


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires deployed infrastructure)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture(scope="session")
def api_base_url():
    """Get API base URL from environment or use default"""
    return os.environ.get(
        'API_BASE_URL',
        'https://o06264kkzj.execute-api.us-east-1.amazonaws.com/prod'
    )


@pytest.fixture(scope="session")
def api_config():
    """Get API configuration"""
    return {
        'base_url': os.environ.get(
            'API_BASE_URL',
            'https://o06264kkzj.execute-api.us-east-1.amazonaws.com/prod'
        ),
        'timeout': int(os.environ.get('API_TIMEOUT', '30')),
        'region': os.environ.get('AWS_REGION', 'us-east-1')
    }
