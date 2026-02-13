"""
Pytest configuration for integration tests
"""
import pytest
import os
import requests
from typing import Dict, Optional


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


class APITestClient:
    """Helper class for making API requests in integration tests"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.access_token: Optional[str] = None
    
    def set_auth_token(self, token: str):
        """Set authentication token for subsequent requests"""
        self.access_token = token
        self.session.headers.update({'Authorization': f'Bearer {token}'})
    
    def clear_auth_token(self):
        """Clear authentication token"""
        self.access_token = None
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make HTTP request to API"""
        url = f"{self.base_url}{path}"
        kwargs.setdefault('timeout', self.timeout)
        return self.session.request(method, url, **kwargs)
    
    def get(self, path: str, **kwargs) -> requests.Response:
        """GET request"""
        return self.request('GET', path, **kwargs)
    
    def post(self, path: str, **kwargs) -> requests.Response:
        """POST request"""
        return self.request('POST', path, **kwargs)
    
    def put(self, path: str, **kwargs) -> requests.Response:
        """PUT request"""
        return self.request('PUT', path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE request"""
        return self.request('DELETE', path, **kwargs)
    
    # Auth endpoints
    def register(self, email: str, password: str, **kwargs) -> Dict:
        """Register a new user"""
        response = self.post('/auth/register', json={
            'email': email,
            'password': password,
            **kwargs
        })
        response.raise_for_status()
        return response.json()
    
    def login(self, email: str, password: str) -> Dict:
        """Login and return tokens"""
        response = self.post('/auth/login', json={
            'email': email,
            'password': password
        })
        response.raise_for_status()
        data = response.json()
        # Auto-set access token for subsequent requests
        if 'access_token' in data:
            self.set_auth_token(data['access_token'])
        return data


@pytest.fixture
def api_client(api_config):
    """Create API test client"""
    return APITestClient(
        base_url=api_config['base_url'],
        timeout=api_config['timeout']
    )
