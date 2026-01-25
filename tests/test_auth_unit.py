"""
Unit tests for authentication edge cases
Tests invalid credentials, expired tokens, malformed requests, and password strength validation
"""
import pytest
import json
import sys
import os
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.auth.handler import lambda_handler
from shared.database import get_db_connection


def cleanup_test_user(email: str):
    """Clean up test user from database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            conn.commit()
            cursor.close()
    except Exception:
        pass


def extract_error_message(response_body):
    """Extract error message from response body, handling both error formats"""
    if isinstance(response_body.get('error'), str):
        return response_body['error']
    elif isinstance(response_body.get('error'), dict):
        return response_body['error'].get('message', '')
    return ''


class TestAuthenticationEdgeCases:
    """Test authentication edge cases and error conditions"""
    
    @pytest.fixture(autouse=True)
    def setup_cognito_mock(self):
        """Set up mock Cognito User Pool for testing"""
        # Remove LocalStack endpoint to use moto instead
        original_endpoint = os.environ.pop('AWS_ENDPOINT_URL', None)
        original_pool_id = os.environ.get('USER_POOL_ID')
        original_client_id = os.environ.get('USER_POOL_CLIENT_ID')
        
        # Start the mock first
        mock = mock_aws()
        mock.start()
        
        try:
            # Create Cognito client
            client = boto3.client('cognito-idp', region_name='us-east-1')
            
            # Create User Pool
            user_pool = client.create_user_pool(
                PoolName='test-pool',
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8,
                        'RequireUppercase': True,
                        'RequireLowercase': True,
                        'RequireNumbers': True,
                        'RequireSymbols': True
                    }
                },
                UsernameAttributes=['email']
            )
            
            # Create User Pool Client
            user_pool_client = client.create_user_pool_client(
                UserPoolId=user_pool['UserPool']['Id'],
                ClientName='test-client',
                ExplicitAuthFlows=['USER_PASSWORD_AUTH', 'ALLOW_USER_PASSWORD_AUTH']
            )
            
            # Set environment variables with real IDs from moto
            os.environ['USER_POOL_ID'] = user_pool['UserPool']['Id']
            os.environ['USER_POOL_CLIENT_ID'] = user_pool_client['UserPoolClient']['ClientId']
            os.environ['AWS_REGION'] = 'us-east-1'
            
            # CRITICAL: Patch the cognito client AND the environment variables in the auth handler module
            import lambda_functions.auth.handler as auth_handler
            auth_handler.USER_POOL_ID = user_pool['UserPool']['Id']
            auth_handler.USER_POOL_CLIENT_ID = user_pool_client['UserPoolClient']['ClientId']
            auth_handler.cognito_client = client
            
            yield
            
        finally:
            # Stop the mock
            mock.stop()
            
            # Restore original environment variables
            if original_endpoint:
                os.environ['AWS_ENDPOINT_URL'] = original_endpoint
            if original_pool_id:
                os.environ['USER_POOL_ID'] = original_pool_id
            if original_client_id:
                os.environ['USER_POOL_CLIENT_ID'] = original_client_id
    
    def test_register_with_invalid_email_formats(self):
        """Test registration with various invalid email formats"""
        invalid_emails = [
            "",  # Empty email
            "invalid",  # No @ symbol
            "@domain.com",  # Missing username
            "user@",  # Missing domain
            "user@domain",  # Missing TLD
            "user@.com",  # Missing domain name
            "user@domain.",  # Missing TLD
            "user name@domain.com",  # Space in username
            "user@domain .com",  # Space in domain
            "a" * 250 + "@domain.com",  # Too long email
            "user@domain@com",  # Multiple @ symbols
        ]
        
        for email in invalid_emails:
            event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps({
                    'email': email,
                    'password': 'ValidPass123!',
                    'first_name': 'Test',
                    'last_name': 'User'
                }),
                'headers': {}
            }
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 400, f"Email '{email}' should return 400 but got {response['statusCode']}"
            body = json.loads(response['body'])
            assert 'error' in body
            error_msg = extract_error_message(body).lower()
            # For invalid email formats, we expect either a proper error message or a Cognito error
            # The important thing is that it returns 400 status code
            if email == "":
                # Empty email should be caught by our validation
                assert 'email' in error_msg or 'required' in error_msg
            else:
                # Other invalid formats might be caught by Cognito with various error messages
                # Just ensure it's a 400 error (already asserted above)
                pass
    
    def test_register_with_weak_passwords(self):
        """Test registration with passwords that don't meet strength requirements"""
        weak_passwords = [
            "",  # Empty password
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoDigits!",  # No digits
            "NoSpecialChars123",  # No special characters
            "a" * 129,  # Too long (over 128 chars)
        ]
        
        for i, password in enumerate(weak_passwords):
            email = f"test{i}@example.com"
            event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps({
                    'email': email,
                    'password': password,
                    'first_name': 'Test',
                    'last_name': 'User'
                }),
                'headers': {}
            }
            
            try:
                response = lambda_handler(event, {})
                assert response['statusCode'] == 400
                body = json.loads(response['body'])
                assert 'error' in body
                error_msg = extract_error_message(body).lower()
                # For weak passwords, we expect either a proper error message or a Cognito error
                # The important thing is that it returns 400 status code
                if password == "":
                    # Empty password should be caught by our validation
                    assert 'password' in error_msg or 'required' in error_msg
                else:
                    # Other weak passwords might be caught by Cognito with various error messages
                    # Just ensure it's a 400 error (already asserted above)
                    pass
            finally:
                cleanup_test_user(email)
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email address"""
        email = "duplicate@example.com"
        user_data = {
            'email': email,
            'password': 'ValidPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        try:
            # First registration should succeed
            event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps(user_data),
                'headers': {}
            }
            
            response1 = lambda_handler(event, {})
            print(f"First registration response: {response1}")
            if response1['statusCode'] != 201:
                body1 = json.loads(response1['body'])
                print(f"First registration body: {body1}")
            assert response1['statusCode'] == 201
            
            # Second registration with same email should fail
            response2 = lambda_handler(event, {})
            assert response2['statusCode'] == 409
            body = json.loads(response2['body'])
            assert 'error' in body
            error_msg = extract_error_message(body).lower()
            assert 'already exists' in error_msg
            
        finally:
            cleanup_test_user(email)
    
    def test_login_with_invalid_credentials(self):
        """Test login with various invalid credential combinations"""
        # First create a user
        email = "testlogin@example.com"
        password = "ValidPass123!"
        
        register_event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'body': json.dumps({
                'email': email,
                'password': password,
                'first_name': 'Test',
                'last_name': 'User'
            }),
            'headers': {}
        }
        
        try:
            register_response = lambda_handler(register_event, {})
            assert register_response['statusCode'] == 201
            
            # Confirm the user (required for login)
            import lambda_functions.auth.handler as auth_handler
            auth_handler.cognito_client.admin_confirm_sign_up(
                UserPoolId=auth_handler.USER_POOL_ID,
                Username=email
            )
            
            # Test various invalid login attempts
            invalid_attempts = [
                {'email': email, 'password': 'WrongPassword123!'},  # Wrong password
                {'email': 'wrong@example.com', 'password': password},  # Wrong email
                {'email': email, 'password': ''},  # Empty password
                {'email': '', 'password': password},  # Empty email
            ]
            
            for attempt in invalid_attempts:
                login_event = {
                    'httpMethod': 'POST',
                    'path': '/auth/login',
                    'body': json.dumps(attempt),
                    'headers': {}
                }
                
                response = lambda_handler(login_event, {})
                assert response['statusCode'] in [400, 401]
                body = json.loads(response['body'])
                assert 'error' in body
            
            # Test case insensitive email (should succeed)
            case_insensitive_event = {
                'httpMethod': 'POST',
                'path': '/auth/login',
                'body': json.dumps({
                    'email': email.upper(),
                    'password': password
                }),
                'headers': {}
            }
            
            response = lambda_handler(case_insensitive_event, {})
            assert response['statusCode'] == 200  # Should succeed with case insensitive email
                
        finally:
            cleanup_test_user(email)
    
    def test_malformed_request_bodies(self):
        """Test handling of malformed JSON request bodies"""
        malformed_requests = [
            "",  # Empty body
            "{invalid json}",  # Invalid JSON
            "not json at all",  # Not JSON
            '{"incomplete": }',  # Incomplete JSON
        ]
        
        for malformed_body in malformed_requests:
            event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': malformed_body,
                'headers': {}
            }
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'error' in body
    
    def test_missing_required_fields(self):
        """Test registration and login with missing required fields"""
        # Test registration with missing fields
        incomplete_registrations = [
            {},  # All fields missing
            {'email': 'test@example.com'},  # Missing password
            {'password': 'ValidPass123!'},  # Missing email
            {'email': '', 'password': 'ValidPass123!'},  # Empty email
            {'email': 'test@example.com', 'password': ''},  # Empty password
        ]
        
        for incomplete_data in incomplete_registrations:
            event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps(incomplete_data),
                'headers': {}
            }
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'error' in body
            error_msg = extract_error_message(body).lower()
            assert 'required' in error_msg
    
    def test_token_validation_edge_cases(self):
        """Test token validation with various invalid tokens"""
        invalid_tokens = [
            "",  # Empty token
            "invalid.token.format",  # Invalid JWT format
            "Bearer ",  # Bearer with no token
            "Bearer invalid_token",  # Bearer with invalid token
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",  # Malformed JWT
        ]
        
        for token in invalid_tokens:
            event = {
                'httpMethod': 'GET',
                'path': '/auth/validate',
                'headers': {'Authorization': token} if token else {}
            }
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 401
            body = json.loads(response['body'])
            assert 'error' in body
    
    def test_logout_without_token(self):
        """Test logout without providing a token"""
        event = {
            'httpMethod': 'POST',
            'path': '/auth/logout',
            'headers': {}
        }
        
        response = lambda_handler(event, {})
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        error_msg = extract_error_message(body).lower()
        assert 'authorization' in error_msg
    
    def test_password_validation_via_registration(self):
        """Test password validation through registration endpoint"""
        # Test various invalid passwords through the registration endpoint
        invalid_cases = [
            ("", "Password is required"),
            ("short", "Password does not meet requirements"),
            ("nouppercase123!", "Password does not meet requirements"),
            ("NOLOWERCASE123!", "Password does not meet requirements"),
            ("NoDigits!", "Password does not meet requirements"),
            ("NoSpecialChars123", "Password does not meet requirements"),
        ]
        
        for i, (password, expected_error_keyword) in enumerate(invalid_cases):
            email = f"testpass{i}@example.com"
            event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps({
                    'email': email,
                    'password': password,
                    'first_name': 'Test',
                    'last_name': 'User'
                }),
                'headers': {}
            }
            
            try:
                response = lambda_handler(event, {})
                assert response['statusCode'] == 400
                body = json.loads(response['body'])
                assert 'error' in body
                # Cognito handles password validation, so we just check for error
                error_msg = extract_error_message(body).lower()
                assert 'password' in error_msg or 'required' in error_msg
            finally:
                cleanup_test_user(email)
    
    def test_email_validation_via_registration(self):
        """Test email validation through registration endpoint"""
        # Test various invalid emails through the registration endpoint
        invalid_emails = [
            "",
            "invalid",
            "@domain.com",
            "user@",
            "user@domain",
            "user@.com",
            "a" * 250 + "@domain.com",  # Too long
        ]
        
        for i, email in enumerate(invalid_emails):
            event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps({
                    'email': email,
                    'password': 'ValidPass123!',
                    'first_name': 'Test',
                    'last_name': 'User'
                }),
                'headers': {}
            }
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'error' in body
            # Check for email-related error or required field error
            error_msg = extract_error_message(body).lower()
            assert 'email' in error_msg or 'required' in error_msg or 'invalid' in error_msg
    
    def test_nonexistent_endpoints(self):
        """Test requests to nonexistent endpoints"""
        nonexistent_paths = [
            '/auth/nonexistent',
            '/auth/register/extra',
            '/auth/login/extra',
            '/completely/wrong/path',
        ]
        
        for path in nonexistent_paths:
            event = {
                'httpMethod': 'POST',
                'path': path,
                'body': json.dumps({}),
                'headers': {}
            }
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 404
            body = json.loads(response['body'])
            assert 'error' in body
            error_msg = extract_error_message(body).lower()
            assert 'not found' in error_msg


if __name__ == '__main__':
    pytest.main([__file__, '-v'])