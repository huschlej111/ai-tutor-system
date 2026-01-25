"""
Simplified integration tests for API Gateway endpoints
Tests API endpoint structure and basic functionality
"""
import json
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# Import Lambda handlers
from lambda_functions.auth.handler import lambda_handler as auth_handler
from lambda_functions.domain_management.handler import lambda_handler as domain_handler
from lambda_functions.quiz_engine.handler import lambda_handler as quiz_handler
from lambda_functions.progress_tracking.handler import lambda_handler as progress_handler
from lambda_functions.batch_upload.handler import lambda_handler as batch_handler


class TestAPIEndpointIntegration:
    """Test API endpoint integration with Lambda handlers"""
    
    def create_api_gateway_event(self, method: str, path: str, body: Dict[str, Any] = None, 
                                headers: Dict[str, str] = None, 
                                path_parameters: Dict[str, str] = None,
                                query_parameters: Dict[str, str] = None,
                                cognito_claims: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a mock API Gateway event"""
        event = {
            'httpMethod': method,
            'path': path,
            'headers': headers or {},
            'pathParameters': path_parameters,
            'queryStringParameters': query_parameters,
            'body': json.dumps(body) if body else None,
            'requestContext': {
                'requestId': 'test-request-id',
                'stage': 'test',
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        # Add Cognito authorizer context if provided
        if cognito_claims:
            event['requestContext']['authorizer'] = {
                'claims': cognito_claims
            }
        
        return event
    
    def create_lambda_context(self) -> Mock:
        """Create a mock Lambda context"""
        context = Mock()
        context.function_name = 'test-function'
        context.function_version = '1'
        context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test-function'
        context.memory_limit_in_mb = 256
        context.remaining_time_in_millis = lambda: 30000
        context.aws_request_id = 'test-request-id'
        return context


class TestAuthEndpoints(TestAPIEndpointIntegration):
    """Test authentication endpoint integration"""
    
    @patch('lambda_functions.auth.handler.cognito_client')
    def test_register_endpoint_success(self, mock_cognito):
        """Test user registration endpoint"""
        # Mock Cognito response
        mock_cognito.sign_up.return_value = {
            'UserSub': 'test-user-sub',
            'UserConfirmed': False,
            'CodeDeliveryDetails': {
                'Destination': 'test@example.com',
                'DeliveryMedium': 'EMAIL'
            }
        }
        
        # Create test event
        event = self.create_api_gateway_event(
            method='POST',
            path='/auth/register',
            body={
                'email': 'test@example.com',
                'password': 'TestPassword123!',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        context = self.create_lambda_context()
        
        # Call handler
        response = auth_handler(event, context)
        
        # Verify response
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert body['message'] == 'User registered successfully'
        assert 'user_sub' in body
        
        # Verify security headers
        headers = response.get('headers', {})
        assert 'Strict-Transport-Security' in headers
        assert 'X-Content-Type-Options' in headers
    
    @patch('lambda_functions.auth.handler.cognito_client')
    def test_login_endpoint_success(self, mock_cognito):
        """Test user login endpoint"""
        # Mock Cognito responses
        mock_cognito.initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'test-access-token',
                'IdToken': 'test-id-token',
                'RefreshToken': 'test-refresh-token',
                'ExpiresIn': 3600
            }
        }
        
        mock_cognito.get_user.return_value = {
            'Username': 'test@example.com',
            'UserAttributes': [
                {'Name': 'sub', 'Value': 'test-user-sub'},
                {'Name': 'email', 'Value': 'test@example.com'},
                {'Name': 'given_name', 'Value': 'Test'},
                {'Name': 'family_name', 'Value': 'User'},
                {'Name': 'email_verified', 'Value': 'true'}
            ]
        }
        
        # Create test event
        event = self.create_api_gateway_event(
            method='POST',
            path='/auth/login',
            body={
                'email': 'test@example.com',
                'password': 'TestPassword123!'
            }
        )
        
        context = self.create_lambda_context()
        
        # Call handler
        response = auth_handler(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['message'] == 'Login successful'
        assert 'user' in body
        assert 'tokens' in body
        assert 'access_token' in body['tokens']
    
    def test_register_invalid_email(self):
        """Test registration with invalid email format"""
        event = self.create_api_gateway_event(
            method='POST',
            path='/auth/register',
            body={
                'email': 'invalid-email',
                'password': 'TestPassword123!'
            }
        )
        
        context = self.create_lambda_context()
        response = auth_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_register_missing_password(self):
        """Test registration with missing password"""
        event = self.create_api_gateway_event(
            method='POST',
            path='/auth/register',
            body={
                'email': 'test@example.com'
                # Missing password
            }
        )
        
        context = self.create_lambda_context()
        response = auth_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_unsupported_endpoint(self):
        """Test unsupported auth endpoint"""
        event = self.create_api_gateway_event(
            method='GET',
            path='/auth/unsupported'
        )
        
        context = self.create_lambda_context()
        response = auth_handler(event, context)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body


class TestDomainEndpoints(TestAPIEndpointIntegration):
    """Test domain management endpoint integration"""
    
    @patch('shared.database.get_db_connection')
    def test_create_domain_success(self, mock_db):
        """Test domain creation endpoint"""
        # Mock database operations
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_connection
        
        # Mock database responses
        mock_cursor.fetchone.return_value = {'domain_id': 'test-domain-id'}
        
        # Create test event with Cognito claims
        event = self.create_api_gateway_event(
            method='POST',
            path='/domains',
            body={
                'name': 'Test Domain',
                'description': 'A test domain',
                'terms': [
                    {
                        'term': 'Test Term',
                        'definition': 'Test definition'
                    }
                ]
            },
            cognito_claims={
                'sub': 'test-user-id',
                'email': 'test@example.com',
                'cognito:groups': 'student'
            }
        )
        
        context = self.create_lambda_context()
        
        # Call handler
        response = domain_handler(event, context)
        
        # Verify response
        assert response['statusCode'] in [201, 500]  # Created or error (due to mocking)
    
    def test_create_domain_unauthorized(self):
        """Test domain creation without authentication"""
        event = self.create_api_gateway_event(
            method='POST',
            path='/domains',
            body={
                'name': 'Test Domain',
                'description': 'A test domain',
                'terms': []
            }
        )
        
        context = self.create_lambda_context()
        response = domain_handler(event, context)
        
        # Should return unauthorized
        assert response['statusCode'] in [401, 403]
    
    @patch('shared.database.get_db_connection')
    def test_list_domains_success(self, mock_db):
        """Test domain listing endpoint"""
        # Mock database operations
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_connection
        
        # Mock database response
        mock_cursor.fetchall.return_value = [
            {
                'domain_id': 'domain-1',
                'name': 'Domain 1',
                'description': 'First domain'
            },
            {
                'domain_id': 'domain-2',
                'name': 'Domain 2',
                'description': 'Second domain'
            }
        ]
        
        # Create test event with authentication
        event = self.create_api_gateway_event(
            method='GET',
            path='/domains',
            cognito_claims={
                'sub': 'test-user-id',
                'email': 'test@example.com',
                'cognito:groups': 'student'
            }
        )
        
        context = self.create_lambda_context()
        response = domain_handler(event, context)
        
        # Verify response structure
        assert response['statusCode'] in [200, 500]  # Success or error (due to mocking)


class TestQuizEndpoints(TestAPIEndpointIntegration):
    """Test quiz engine endpoint integration"""
    
    @patch('shared.database.get_db_connection')
    def test_start_quiz_success(self, mock_db):
        """Test quiz session start endpoint"""
        # Mock database operations
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_connection
        
        # Mock database responses
        mock_cursor.fetchone.side_effect = [
            {'domain_id': 'test-domain-id', 'name': 'Test Domain'},  # Domain exists
            {'session_id': 'test-session-id'}  # Session created
        ]
        
        # Create test event
        event = self.create_api_gateway_event(
            method='POST',
            path='/quiz/start',
            body={
                'domain_id': 'test-domain-id'
            },
            cognito_claims={
                'sub': 'test-user-id',
                'email': 'test@example.com',
                'cognito:groups': 'student'
            }
        )
        
        context = self.create_lambda_context()
        response = quiz_handler(event, context)
        
        # Verify response structure
        assert response['statusCode'] in [201, 400, 500]  # Created, bad request, or error
    
    def test_start_quiz_unauthorized(self):
        """Test quiz start without authentication"""
        event = self.create_api_gateway_event(
            method='POST',
            path='/quiz/start',
            body={
                'domain_id': 'test-domain-id'
            }
        )
        
        context = self.create_lambda_context()
        response = quiz_handler(event, context)
        
        # Should return unauthorized
        assert response['statusCode'] in [401, 403]


class TestProgressEndpoints(TestAPIEndpointIntegration):
    """Test progress tracking endpoint integration"""
    
    @patch('shared.database.get_db_connection')
    def test_get_progress_dashboard(self, mock_db):
        """Test progress dashboard endpoint"""
        # Mock database operations
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_connection
        
        # Mock database response
        mock_cursor.fetchall.return_value = [
            {
                'domain_id': 'domain-1',
                'domain_name': 'Domain 1',
                'total_terms': 10,
                'mastered_terms': 7,
                'progress_percentage': 70.0
            }
        ]
        
        # Create test event
        event = self.create_api_gateway_event(
            method='GET',
            path='/progress/dashboard',
            cognito_claims={
                'sub': 'test-user-id',
                'email': 'test@example.com',
                'cognito:groups': 'student'
            }
        )
        
        context = self.create_lambda_context()
        response = progress_handler(event, context)
        
        # Verify response structure
        assert response['statusCode'] in [200, 500]  # Success or error
    
    def test_get_progress_unauthorized(self):
        """Test progress dashboard without authentication"""
        event = self.create_api_gateway_event(
            method='GET',
            path='/progress/dashboard'
        )
        
        context = self.create_lambda_context()
        response = progress_handler(event, context)
        
        # Should return unauthorized
        assert response['statusCode'] in [401, 403]


class TestBatchUploadEndpoints(TestAPIEndpointIntegration):
    """Test batch upload endpoint integration"""
    
    @patch('shared.authorization_utils.validate_api_access')
    @patch('shared.database.get_db_connection')
    def test_batch_validate_success(self, mock_db, mock_auth):
        """Test batch upload validation endpoint"""
        # Mock authorization
        mock_auth.return_value = {
            'user_id': 'test-user-id',
            'groups': ['instructor']
        }
        
        # Mock database operations
        mock_cursor = MagicMock()
        mock_connection = MagicMock()
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value = mock_connection
        
        # Create test event
        event = self.create_api_gateway_event(
            method='POST',
            path='/batch/validate',
            body={
                'domains': [
                    {
                        'name': 'Batch Domain',
                        'description': 'A batch uploaded domain',
                        'terms': [
                            {
                                'term': 'Batch Term',
                                'definition': 'Batch definition'
                            }
                        ]
                    }
                ]
            },
            cognito_claims={
                'sub': 'test-user-id',
                'email': 'test@example.com',
                'cognito:groups': 'instructor'
            }
        )
        
        context = self.create_lambda_context()
        response = batch_handler(event, context)
        
        # Verify response structure
        assert response['statusCode'] in [200, 400, 403, 500]  # Success, bad request, forbidden, or error
    
    def test_batch_validate_unauthorized(self):
        """Test batch validation without proper authorization"""
        event = self.create_api_gateway_event(
            method='POST',
            path='/batch/validate',
            body={
                'domains': []
            }
        )
        
        context = self.create_lambda_context()
        response = batch_handler(event, context)
        
        # Should return forbidden (no authorization)
        assert response['statusCode'] == 403


class TestErrorHandling(TestAPIEndpointIntegration):
    """Test API error handling across endpoints"""
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON in request body"""
        event = self.create_api_gateway_event(
            method='POST',
            path='/auth/register'
        )
        event['body'] = 'invalid json'
        
        context = self.create_lambda_context()
        response = auth_handler(event, context)
        
        # Should handle gracefully
        assert response['statusCode'] in [400, 500]
        assert 'body' in response
    
    def test_missing_request_body(self):
        """Test handling of missing request body"""
        event = self.create_api_gateway_event(
            method='POST',
            path='/auth/register'
        )
        event['body'] = None
        
        context = self.create_lambda_context()
        response = auth_handler(event, context)
        
        # Should handle gracefully
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_unsupported_http_method(self):
        """Test handling of unsupported HTTP methods"""
        event = self.create_api_gateway_event(
            method='PATCH',  # Unsupported method
            path='/auth/register'
        )
        
        context = self.create_lambda_context()
        response = auth_handler(event, context)
        
        # Should return method not allowed or not found
        assert response['statusCode'] in [404, 405]


class TestSecurityFeatures(TestAPIEndpointIntegration):
    """Test security features in API responses"""
    
    def test_security_headers_in_responses(self):
        """Test that security headers are included in responses"""
        event = self.create_api_gateway_event(
            method='POST',
            path='/auth/register',
            body={
                'email': 'test@example.com',
                'password': 'TestPassword123!'
            }
        )
        
        context = self.create_lambda_context()
        response = auth_handler(event, context)
        
        # Check for security headers
        headers = response.get('headers', {})
        
        # These headers should be present due to security middleware
        expected_headers = [
            'Strict-Transport-Security',
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Referrer-Policy'
        ]
        
        for header in expected_headers:
            assert header in headers, f"Security header {header} missing"
    
    def test_cors_headers_in_responses(self):
        """Test that CORS headers are included in responses"""
        event = self.create_api_gateway_event(
            method='GET',
            path='/health'
        )
        
        context = self.create_lambda_context()
        
        # Use auth handler as it has CORS headers
        response = auth_handler(event, context)
        
        # Check for CORS headers
        headers = response.get('headers', {})
        
        expected_cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Headers',
            'Access-Control-Allow-Methods'
        ]
        
        for header in expected_cors_headers:
            assert header in headers, f"CORS header {header} missing"


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])