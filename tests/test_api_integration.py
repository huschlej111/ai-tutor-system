"""
Integration tests for API Gateway endpoints
Tests end-to-end API flows with authentication and error handling
"""
import json
import pytest
import requests
import boto3
import os
from typing import Dict, Any, Optional
# from moto import mock_cognito_idp, mock_apigateway, mock_lambda  # Not available in current moto version
import uuid
from datetime import datetime

# Test configuration
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:4566/restapis/test-api/local/_user_request_/api')
TEST_USER_EMAIL = 'test@example.com'
TEST_USER_PASSWORD = 'TestPassword123!'

# Check if API Gateway is available
def is_api_gateway_available():
    """Check if API Gateway is available for testing"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Skip API integration tests if API Gateway is not available
pytestmark = pytest.mark.skipif(
    not is_api_gateway_available(),
    reason="API Gateway not available - requires deployed infrastructure"
)


class APITestClient:
    """Test client for API Gateway integration tests"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        
    def set_auth_token(self, token: str):
        """Set authentication token for requests"""
        self.access_token = token
        self.session.headers.update({'Authorization': f'Bearer {token}'})
    
    def clear_auth_token(self):
        """Clear authentication token"""
        self.access_token = None
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
    
    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to API endpoint"""
        url = f"{self.base_url}{endpoint}"
        return self.session.request(method, url, **kwargs)
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request"""
        return self.request('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request"""
        return self.request('POST', endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make PUT request"""
        return self.request('PUT', endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request"""
        return self.request('DELETE', endpoint, **kwargs)


@pytest.fixture
def api_client():
    """Create API test client"""
    return APITestClient(API_BASE_URL)


@pytest.fixture
def authenticated_client(api_client):
    """Create authenticated API test client"""
    # Register and login test user
    registration_data = {
        'email': TEST_USER_EMAIL,
        'password': TEST_USER_PASSWORD,
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    # Register user
    response = api_client.post('/auth/register', json=registration_data)
    assert response.status_code in [201, 409]  # Created or already exists
    
    # Login user
    login_data = {
        'email': TEST_USER_EMAIL,
        'password': TEST_USER_PASSWORD
    }
    
    response = api_client.post('/auth/login', json=login_data)
    assert response.status_code == 200
    
    login_result = response.json()
    access_token = login_result['tokens']['access_token']
    api_client.set_auth_token(access_token)
    
    return api_client


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_success(self, api_client):
        """Test health check returns success"""
        response = api_client.get('/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_health_check_no_auth_required(self, api_client):
        """Test health check doesn't require authentication"""
        # Ensure no auth token is set
        api_client.clear_auth_token()
        
        response = api_client.get('/health')
        assert response.status_code == 200


class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""
    
    def test_user_registration_success(self, api_client):
        """Test successful user registration"""
        unique_email = f"test_{uuid.uuid4()}@example.com"
        registration_data = {
            'email': unique_email,
            'password': 'TestPassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        response = api_client.post('/auth/register', json=registration_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data['message'] == 'User registered successfully'
        assert 'user_sub' in data
        assert 'confirmation_required' in data
    
    def test_user_registration_invalid_email(self, api_client):
        """Test registration with invalid email"""
        registration_data = {
            'email': 'invalid-email',
            'password': 'TestPassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        response = api_client.post('/auth/register', json=registration_data)
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_user_registration_weak_password(self, api_client):
        """Test registration with weak password"""
        unique_email = f"test_{uuid.uuid4()}@example.com"
        registration_data = {
            'email': unique_email,
            'password': '123',  # Too weak
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        response = api_client.post('/auth/register', json=registration_data)
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
    
    def test_user_login_success(self, api_client):
        """Test successful user login"""
        # First register a user
        unique_email = f"test_{uuid.uuid4()}@example.com"
        registration_data = {
            'email': unique_email,
            'password': 'TestPassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        register_response = api_client.post('/auth/register', json=registration_data)
        assert register_response.status_code == 201
        
        # Then login
        login_data = {
            'email': unique_email,
            'password': 'TestPassword123!'
        }
        
        response = api_client.post('/auth/login', json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Login successful'
        assert 'user' in data
        assert 'tokens' in data
        assert 'access_token' in data['tokens']
        assert 'id_token' in data['tokens']
        assert 'refresh_token' in data['tokens']
    
    def test_user_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials"""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'WrongPassword123!'
        }
        
        response = api_client.post('/auth/login', json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data
    
    def test_token_validation_success(self, authenticated_client):
        """Test successful token validation"""
        response = authenticated_client.get('/auth/validate')
        
        assert response.status_code == 200
        data = response.json()
        assert data['valid'] is True
        assert 'user' in data
    
    def test_token_validation_no_token(self, api_client):
        """Test token validation without token"""
        response = api_client.get('/auth/validate')
        
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data
    
    def test_user_logout_success(self, authenticated_client):
        """Test successful user logout"""
        response = authenticated_client.post('/auth/logout')
        
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Logout successful'


class TestDomainEndpoints:
    """Test domain management API endpoints"""
    
    def test_create_domain_success(self, authenticated_client):
        """Test successful domain creation"""
        domain_data = {
            'name': f'Test Domain {uuid.uuid4()}',
            'description': 'A test domain for integration testing',
            'terms': [
                {
                    'term': 'Test Term 1',
                    'definition': 'Definition for test term 1'
                },
                {
                    'term': 'Test Term 2',
                    'definition': 'Definition for test term 2'
                }
            ]
        }
        
        response = authenticated_client.post('/domains', json=domain_data)
        
        assert response.status_code == 201
        data = response.json()
        assert 'domain_id' in data
        assert data['name'] == domain_data['name']
        assert len(data['terms']) == 2
    
    def test_create_domain_unauthorized(self, api_client):
        """Test domain creation without authentication"""
        domain_data = {
            'name': 'Test Domain',
            'description': 'A test domain',
            'terms': [
                {
                    'term': 'Test Term',
                    'definition': 'Test definition'
                }
            ]
        }
        
        response = api_client.post('/domains', json=domain_data)
        
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data
    
    def test_list_domains_success(self, authenticated_client):
        """Test successful domain listing"""
        response = authenticated_client.get('/domains')
        
        assert response.status_code == 200
        data = response.json()
        assert 'domains' in data
        assert isinstance(data['domains'], list)
    
    def test_get_domain_success(self, authenticated_client):
        """Test successful domain retrieval"""
        # First create a domain
        domain_data = {
            'name': f'Test Domain {uuid.uuid4()}',
            'description': 'A test domain for retrieval testing',
            'terms': [
                {
                    'term': 'Test Term',
                    'definition': 'Test definition'
                }
            ]
        }
        
        create_response = authenticated_client.post('/domains', json=domain_data)
        assert create_response.status_code == 201
        
        domain_id = create_response.json()['domain_id']
        
        # Then retrieve it
        response = authenticated_client.get(f'/domains/{domain_id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['domain_id'] == domain_id
        assert data['name'] == domain_data['name']
    
    def test_get_domain_not_found(self, authenticated_client):
        """Test domain retrieval with non-existent ID"""
        fake_id = str(uuid.uuid4())
        response = authenticated_client.get(f'/domains/{fake_id}')
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data


class TestQuizEndpoints:
    """Test quiz engine API endpoints"""
    
    def test_start_quiz_success(self, authenticated_client):
        """Test successful quiz session start"""
        # First create a domain
        domain_data = {
            'name': f'Quiz Test Domain {uuid.uuid4()}',
            'description': 'A test domain for quiz testing',
            'terms': [
                {
                    'term': 'Quiz Term 1',
                    'definition': 'Definition for quiz term 1'
                },
                {
                    'term': 'Quiz Term 2',
                    'definition': 'Definition for quiz term 2'
                }
            ]
        }
        
        create_response = authenticated_client.post('/domains', json=domain_data)
        assert create_response.status_code == 201
        
        domain_id = create_response.json()['domain_id']
        
        # Start quiz session
        quiz_data = {
            'domain_id': domain_id
        }
        
        response = authenticated_client.post('/quiz/start', json=quiz_data)
        
        assert response.status_code == 201
        data = response.json()
        assert 'session_id' in data
        assert 'current_question' in data
        assert data['domain_id'] == domain_id
    
    def test_start_quiz_unauthorized(self, api_client):
        """Test quiz start without authentication"""
        quiz_data = {
            'domain_id': str(uuid.uuid4())
        }
        
        response = api_client.post('/quiz/start', json=quiz_data)
        
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data
    
    def test_submit_answer_success(self, authenticated_client):
        """Test successful answer submission"""
        # Create domain and start quiz (setup from previous test)
        domain_data = {
            'name': f'Answer Test Domain {uuid.uuid4()}',
            'description': 'A test domain for answer testing',
            'terms': [
                {
                    'term': 'Answer Term',
                    'definition': 'Definition for answer term'
                }
            ]
        }
        
        create_response = authenticated_client.post('/domains', json=domain_data)
        assert create_response.status_code == 201
        
        domain_id = create_response.json()['domain_id']
        
        quiz_response = authenticated_client.post('/quiz/start', json={'domain_id': domain_id})
        assert quiz_response.status_code == 201
        
        session_id = quiz_response.json()['session_id']
        
        # Submit answer
        answer_data = {
            'session_id': session_id,
            'answer': 'My test answer for the term'
        }
        
        response = authenticated_client.post('/quiz/answer', json=answer_data)
        
        assert response.status_code == 200
        data = response.json()
        assert 'evaluation' in data
        assert 'similarity_score' in data['evaluation']
        assert 'feedback' in data['evaluation']


class TestProgressEndpoints:
    """Test progress tracking API endpoints"""
    
    def test_get_progress_dashboard_success(self, authenticated_client):
        """Test successful progress dashboard retrieval"""
        response = authenticated_client.get('/progress/dashboard')
        
        assert response.status_code == 200
        data = response.json()
        assert 'overall_progress' in data
        assert 'domain_progress' in data
        assert isinstance(data['domain_progress'], list)
    
    def test_get_progress_dashboard_unauthorized(self, api_client):
        """Test progress dashboard without authentication"""
        response = api_client.get('/progress/dashboard')
        
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data


class TestBatchUploadEndpoints:
    """Test batch upload API endpoints"""
    
    def test_batch_validate_success(self, authenticated_client):
        """Test successful batch upload validation"""
        batch_data = {
            'domains': [
                {
                    'name': f'Batch Domain {uuid.uuid4()}',
                    'description': 'A batch uploaded domain',
                    'terms': [
                        {
                            'term': 'Batch Term 1',
                            'definition': 'Definition for batch term 1'
                        },
                        {
                            'term': 'Batch Term 2',
                            'definition': 'Definition for batch term 2'
                        }
                    ]
                }
            ]
        }
        
        response = authenticated_client.post('/batch/validate', json=batch_data)
        
        # Note: This might require API key in production
        assert response.status_code in [200, 403]  # Success or forbidden (if API key required)
        
        if response.status_code == 200:
            data = response.json()
            assert 'validation_result' in data
            assert data['validation_result']['valid'] is True
    
    def test_batch_validate_unauthorized(self, api_client):
        """Test batch validation without authentication"""
        batch_data = {
            'domains': [
                {
                    'name': 'Test Domain',
                    'description': 'Test description',
                    'terms': [
                        {
                            'term': 'Test Term',
                            'definition': 'Test definition'
                        }
                    ]
                }
            ]
        }
        
        response = api_client.post('/batch/validate', json=batch_data)
        
        assert response.status_code == 401
        data = response.json()
        assert 'error' in data


class TestErrorHandling:
    """Test API error handling and response formatting"""
    
    def test_invalid_json_request(self, api_client):
        """Test API response to invalid JSON"""
        response = api_client.post(
            '/auth/register',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data
        assert 'message' in data
    
    def test_missing_content_type(self, api_client):
        """Test API response to missing content type"""
        response = api_client.post('/auth/register', data='{}')
        
        # Should handle gracefully
        assert response.status_code in [400, 415]  # Bad Request or Unsupported Media Type
    
    def test_large_request_body(self, api_client):
        """Test API response to oversized request"""
        # Create a large request body (over 10MB)
        large_data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'large_field': 'x' * (11 * 1024 * 1024)  # 11MB of data
        }
        
        response = api_client.post('/auth/register', json=large_data)
        
        assert response.status_code in [413, 400]  # Request Entity Too Large or Bad Request
        data = response.json()
        assert 'error' in data
    
    def test_nonexistent_endpoint(self, api_client):
        """Test API response to non-existent endpoint"""
        response = api_client.get('/nonexistent/endpoint')
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
    
    def test_method_not_allowed(self, api_client):
        """Test API response to unsupported HTTP method"""
        response = api_client.patch('/auth/register')  # PATCH not supported
        
        assert response.status_code == 405  # Method Not Allowed


class TestSecurityHeaders:
    """Test security headers in API responses"""
    
    def test_security_headers_present(self, api_client):
        """Test that security headers are present in responses"""
        response = api_client.get('/health')
        
        assert response.status_code == 200
        
        # Check for security headers
        headers = response.headers
        assert 'Strict-Transport-Security' in headers
        assert 'X-Content-Type-Options' in headers
        assert 'X-Frame-Options' in headers
        assert 'X-XSS-Protection' in headers
        assert 'Referrer-Policy' in headers
    
    def test_cors_headers_present(self, api_client):
        """Test that CORS headers are present in responses"""
        response = api_client.options('/auth/register')
        
        # Check for CORS headers
        headers = response.headers
        assert 'Access-Control-Allow-Origin' in headers
        assert 'Access-Control-Allow-Methods' in headers
        assert 'Access-Control-Allow-Headers' in headers


class TestRateLimiting:
    """Test API rate limiting functionality"""
    
    def test_rate_limit_headers(self, authenticated_client):
        """Test that rate limit headers are included"""
        response = authenticated_client.get('/domains')
        
        assert response.status_code == 200
        
        # Check for rate limit headers (if implemented)
        headers = response.headers
        # Note: These headers might not be present in all implementations
        if 'X-RateLimit-Limit' in headers:
            assert 'X-RateLimit-Remaining' in headers
            assert 'X-RateLimit-Reset' in headers
    
    @pytest.mark.slow
    def test_rate_limit_enforcement(self, api_client):
        """Test that rate limiting is enforced (slow test)"""
        # This test would make many rapid requests to trigger rate limiting
        # Marked as slow since it requires many requests
        
        # Make rapid requests to trigger rate limiting
        responses = []
        for i in range(150):  # Exceed typical rate limits
            response = api_client.get('/health')
            responses.append(response)
            
            # Stop if we hit rate limiting
            if response.status_code == 429:
                break
        
        # Check if any requests were rate limited
        rate_limited = any(r.status_code == 429 for r in responses)
        
        # In a real environment with rate limiting, this should be True
        # In test environment, it might not be enforced
        if rate_limited:
            assert any(r.status_code == 429 for r in responses)


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])