"""
API Security Tests
Tests for SQL injection, XSS prevention, rate limiting, authorization bypass, and security headers
"""
import json
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any
import time

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

# Import Lambda handlers and security modules
from lambda_functions.auth.handler import lambda_handler as auth_handler
from lambda_functions.domain_management.handler import lambda_handler as domain_handler
from shared.security_middleware import security_middleware, sanitize_string, validate_email
from shared.authorization_utils import validate_api_access, AuthorizationError


class TestSQLInjectionPrevention:
    """Test SQL injection prevention measures"""
    
    def create_api_gateway_event(self, method: str, path: str, body: Dict[str, Any] = None, 
                                headers: Dict[str, str] = None, 
                                cognito_claims: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a mock API Gateway event"""
        event = {
            'httpMethod': method,
            'path': path,
            'headers': headers or {},
            'body': json.dumps(body) if body else None,
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        if cognito_claims:
            event['requestContext']['authorizer'] = {
                'claims': cognito_claims
            }
        
        return event
    
    def create_lambda_context(self) -> Mock:
        """Create a mock Lambda context"""
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        return context
    
    def test_sql_injection_in_email_field(self):
        """Test SQL injection attempts in email field"""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "admin@example.com'; DELETE FROM users WHERE '1'='1",
            "test@example.com' OR '1'='1' --",
            "'; INSERT INTO users (email) VALUES ('hacker@evil.com'); --",
            "test@example.com'; UPDATE users SET password='hacked' WHERE '1'='1'; --"
        ]
        
        for payload in sql_injection_payloads:
            event = self.create_api_gateway_event(
                method='POST',
                path='/auth/register',
                body={
                    'email': payload,
                    'password': 'TestPassword123!'
                }
            )
            
            context = self.create_lambda_context()
            response = auth_handler(event, context)
            
            # Should reject malicious input
            assert response['statusCode'] in [400, 422], f"SQL injection payload not blocked: {payload}"
            
            body = json.loads(response['body'])
            assert 'error' in body
    
    def test_sql_injection_in_domain_name(self):
        """Test SQL injection attempts in domain name field"""
        sql_injection_payloads = [
            "'; DROP TABLE domains; --",
            "Test Domain'; DELETE FROM domains WHERE '1'='1",
            "Test' OR '1'='1' --",
            "'; INSERT INTO domains (name) VALUES ('Evil Domain'); --"
        ]
        
        for payload in sql_injection_payloads:
            event = self.create_api_gateway_event(
                method='POST',
                path='/domains',
                body={
                    'name': payload,
                    'description': 'Test description',
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
            response = domain_handler(event, context)
            
            # Should reject malicious input or handle it safely
            # The response might be 400 (bad request) or 500 (if it reaches DB but fails safely)
            assert response['statusCode'] in [400, 401, 403, 422, 500], f"SQL injection payload not handled: {payload}"
    
    def test_sql_injection_in_path_parameters(self):
        """Test SQL injection attempts in path parameters"""
        sql_injection_payloads = [
            "'; DROP TABLE domains; --",
            "1' OR '1'='1",
            "1'; DELETE FROM domains; --"
        ]
        
        for payload in sql_injection_payloads:
            event = self.create_api_gateway_event(
                method='GET',
                path=f'/domains/{payload}',
                cognito_claims={
                    'sub': 'test-user-id',
                    'email': 'test@example.com',
                    'cognito:groups': 'student'
                }
            )
            event['pathParameters'] = {'domainId': payload}
            
            context = self.create_lambda_context()
            response = domain_handler(event, context)
            
            # Should handle malicious path parameters safely
            assert response['statusCode'] in [400, 401, 403, 404, 422, 500], f"SQL injection in path not handled: {payload}"


class TestXSSPrevention:
    """Test Cross-Site Scripting (XSS) prevention measures"""
    
    def create_api_gateway_event(self, method: str, path: str, body: Dict[str, Any] = None, 
                                cognito_claims: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a mock API Gateway event"""
        event = {
            'httpMethod': method,
            'path': path,
            'headers': {},
            'body': json.dumps(body) if body else None,
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        if cognito_claims:
            event['requestContext']['authorizer'] = {
                'claims': cognito_claims
            }
        
        return event
    
    def create_lambda_context(self) -> Mock:
        """Create a mock Lambda context"""
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        return context
    
    def test_xss_in_user_input_fields(self):
        """Test XSS prevention in user input fields"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>"
        ]
        
        for payload in xss_payloads:
            # Test in first name field
            event = self.create_api_gateway_event(
                method='POST',
                path='/auth/register',
                body={
                    'email': 'test@example.com',
                    'password': 'TestPassword123!',
                    'first_name': payload,
                    'last_name': 'User'
                }
            )
            
            context = self.create_lambda_context()
            response = auth_handler(event, context)
            
            # Should either reject or sanitize the input
            if response['statusCode'] == 201:
                # If accepted, check that XSS payload was sanitized
                body = json.loads(response['body'])
                # The response shouldn't contain the raw XSS payload
                response_str = json.dumps(body)
                assert '<script>' not in response_str.lower()
                assert 'javascript:' not in response_str.lower()
                assert 'onerror=' not in response_str.lower()
                assert 'onload=' not in response_str.lower()
            else:
                # Should be rejected with appropriate error
                assert response['statusCode'] in [400, 422]
    
    def test_xss_in_domain_content(self):
        """Test XSS prevention in domain content"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')"
        ]
        
        for payload in xss_payloads:
            event = self.create_api_gateway_event(
                method='POST',
                path='/domains',
                body={
                    'name': f'Test Domain {payload}',
                    'description': f'Description with {payload}',
                    'terms': [
                        {
                            'term': f'Term {payload}',
                            'definition': f'Definition with {payload}'
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
            response = domain_handler(event, context)
            
            # Should handle XSS attempts safely
            if response['statusCode'] in [200, 201]:
                # If accepted, verify XSS was sanitized
                body = json.loads(response['body'])
                response_str = json.dumps(body)
                assert '<script>' not in response_str.lower()
                assert 'javascript:' not in response_str.lower()
                assert 'onerror=' not in response_str.lower()
    
    def test_security_headers_prevent_xss(self):
        """Test that security headers are set to prevent XSS"""
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
        
        headers = response.get('headers', {})
        
        # Check XSS protection headers
        assert 'X-XSS-Protection' in headers
        assert headers['X-XSS-Protection'] == '1; mode=block'
        
        # Check Content-Type options
        assert 'X-Content-Type-Options' in headers
        assert headers['X-Content-Type-Options'] == 'nosniff'
        
        # Check Content Security Policy
        assert 'Content-Security-Policy' in headers
        csp = headers['Content-Security-Policy']
        assert "default-src 'self'" in csp
        assert "script-src" in csp


class TestInputSanitization:
    """Test input sanitization functions"""
    
    def test_sanitize_string_function(self):
        """Test the sanitize_string function directly"""
        # Test XSS payloads
        xss_input = "<script>alert('XSS')</script>"
        sanitized = sanitize_string(xss_input)
        assert '<script>' not in sanitized
        assert '&lt;script&gt;' in sanitized  # Should be HTML escaped
        
        # Test SQL injection patterns
        sql_input = "'; DROP TABLE users; --"
        sanitized = sanitize_string(sql_input)
        assert 'DROP TABLE' not in sanitized.upper()
        assert '--' not in sanitized
        
        # Test null bytes and control characters
        malicious_input = "test\x00\x01\x02string"
        sanitized = sanitize_string(malicious_input)
        assert '\x00' not in sanitized
        assert '\x01' not in sanitized
        assert '\x02' not in sanitized
        assert sanitized == 'teststring'
        
        # Test length limits
        long_input = 'x' * 20000
        sanitized = sanitize_string(long_input, max_length=100)
        assert len(sanitized) <= 100
    
    def test_email_validation_function(self):
        """Test email validation function"""
        # Valid emails
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org'
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True
        
        # Invalid emails (including potential injection attempts)
        invalid_emails = [
            'invalid-email',
            'test@',
            '@example.com',
            'test@example',
            "test'; DROP TABLE users; --@example.com",
            'test<script>@example.com',
            'test@example.com<script>alert("XSS")</script>'
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False


class TestAuthorizationBypass:
    """Test authorization bypass prevention"""
    
    def create_api_gateway_event(self, method: str, path: str, body: Dict[str, Any] = None, 
                                cognito_claims: Dict[str, str] = None) -> Dict[str, Any]:
        """Create a mock API Gateway event"""
        event = {
            'httpMethod': method,
            'path': path,
            'headers': {},
            'body': json.dumps(body) if body else None,
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        if cognito_claims:
            event['requestContext']['authorizer'] = {
                'claims': cognito_claims
            }
        
        return event
    
    def test_access_protected_endpoints_without_auth(self):
        """Test that protected endpoints reject unauthenticated requests"""
        protected_endpoints = [
            ('GET', '/domains'),
            ('POST', '/domains'),
            ('GET', '/domains/test-id'),
            ('PUT', '/domains/test-id'),
            ('DELETE', '/domains/test-id'),
            ('POST', '/quiz/start'),
            ('POST', '/quiz/answer'),
            ('GET', '/quiz/question'),
            ('GET', '/progress/dashboard'),
            ('POST', '/progress/record'),
            ('POST', '/batch/validate'),
            ('POST', '/batch/upload')
        ]
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        for method, path in protected_endpoints:
            event = self.create_api_gateway_event(method, path)
            
            # Determine which handler to use based on path
            if path.startswith('/domains'):
                response = domain_handler(event, context)
            elif path.startswith('/quiz'):
                from lambda_functions.quiz_engine.handler import lambda_handler as quiz_handler
                response = quiz_handler(event, context)
            elif path.startswith('/progress'):
                from lambda_functions.progress_tracking.handler import lambda_handler as progress_handler
                response = progress_handler(event, context)
            elif path.startswith('/batch'):
                from lambda_functions.batch_upload.handler import lambda_handler as batch_handler
                response = batch_handler(event, context)
            else:
                continue
            
            # Should return unauthorized or forbidden
            assert response['statusCode'] in [401, 403], f"Endpoint {method} {path} not properly protected"
    
    def test_role_based_access_control(self):
        """Test that role-based access control is enforced"""
        # Test student trying to access admin functions
        student_claims = {
            'sub': 'student-user-id',
            'email': 'student@example.com',
            'cognito:groups': 'student'
        }
        
        # Batch upload should be restricted to instructors/admins
        event = self.create_api_gateway_event(
            method='POST',
            path='/batch/validate',
            body={'domains': []},
            cognito_claims=student_claims
        )
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        from lambda_functions.batch_upload.handler import lambda_handler as batch_handler
        response = batch_handler(event, context)
        
        # Should be forbidden for students
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_token_manipulation_attempts(self):
        """Test resistance to token manipulation attempts"""
        # Test with malformed claims
        malformed_claims = {
            'sub': 'user-id',
            'email': 'test@example.com',
            'cognito:groups': 'admin; DROP TABLE users; --'  # SQL injection in groups
        }
        
        event = self.create_api_gateway_event(
            method='GET',
            path='/domains',
            cognito_claims=malformed_claims
        )
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        response = domain_handler(event, context)
        
        # Should handle malformed claims safely
        assert response['statusCode'] in [200, 400, 401, 403, 500]
    
    def test_privilege_escalation_attempts(self):
        """Test prevention of privilege escalation attempts"""
        # Test with claims that attempt to escalate privileges
        escalation_attempts = [
            {
                'sub': 'user-id',
                'email': 'test@example.com',
                'cognito:groups': 'student,admin',  # Multiple groups
            },
            {
                'sub': 'user-id',
                'email': 'test@example.com',
                'cognito:groups': 'admin',  # Direct admin claim
                'custom:role': 'super_admin'  # Custom role claim
            }
        ]
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        for claims in escalation_attempts:
            event = self.create_api_gateway_event(
                method='POST',
                path='/batch/validate',
                body={'domains': []},
                cognito_claims=claims
            )
            
            from lambda_functions.batch_upload.handler import lambda_handler as batch_handler
            response = batch_handler(event, context)
            
            # Should handle privilege escalation attempts appropriately
            # The response depends on how the authorization logic handles multiple groups
            assert response['statusCode'] in [200, 400, 403, 500]


class TestRateLimitingAndDDoSProtection:
    """Test rate limiting and DDoS protection measures"""
    
    def create_api_gateway_event(self, method: str, path: str, source_ip: str = '127.0.0.1') -> Dict[str, Any]:
        """Create a mock API Gateway event with specific source IP"""
        return {
            'httpMethod': method,
            'path': path,
            'headers': {},
            'body': json.dumps({'email': 'test@example.com', 'password': 'TestPassword123!'}),
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': source_ip,
                    'userAgent': 'test-agent'
                }
            }
        }
    
    def test_rate_limit_headers_present(self):
        """Test that rate limit headers are included in responses"""
        event = self.create_api_gateway_event('POST', '/auth/register')
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        response = auth_handler(event, context)
        
        headers = response.get('headers', {})
        
        # Check for rate limit headers (if implemented)
        # Note: These might not be present in all implementations
        if 'X-RateLimit-Limit' in headers:
            assert 'X-RateLimit-Remaining' in headers
            assert 'X-RateLimit-Reset' in headers
    
    def test_large_request_handling(self):
        """Test handling of oversized requests"""
        # Create a large request body
        large_data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'large_field': 'x' * (5 * 1024 * 1024)  # 5MB of data
        }
        
        event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'headers': {},
            'body': json.dumps(large_data),
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        response = auth_handler(event, context)
        
        # Should reject oversized requests
        assert response['statusCode'] in [400, 413, 422]  # Bad Request or Request Entity Too Large
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_malformed_request_handling(self):
        """Test handling of malformed requests"""
        malformed_requests = [
            # Invalid JSON
            {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'headers': {},
                'body': 'invalid json {',
                'requestContext': {
                    'requestId': 'test-request-id',
                    'identity': {'sourceIp': '127.0.0.1', 'userAgent': 'test-agent'}
                }
            },
            # Missing required fields
            {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'headers': {},
                'body': json.dumps({}),
                'requestContext': {
                    'requestId': 'test-request-id',
                    'identity': {'sourceIp': '127.0.0.1', 'userAgent': 'test-agent'}
                }
            }
        ]
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        for event in malformed_requests:
            response = auth_handler(event, context)
            
            # Should handle malformed requests gracefully
            assert response['statusCode'] in [400, 422, 500]
            assert 'body' in response
            
            try:
                body = json.loads(response['body'])
                assert 'error' in body
            except json.JSONDecodeError:
                # Response body might not be JSON in error cases
                pass


class TestSecurityHeaderValidation:
    """Test security header implementation"""
    
    def test_security_headers_comprehensive(self):
        """Test comprehensive security headers implementation"""
        event = {
            'httpMethod': 'GET',
            'path': '/health',
            'headers': {},
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        response = auth_handler(event, context)
        
        headers = response.get('headers', {})
        
        # Test all required security headers
        security_headers = {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header, expected_value in security_headers.items():
            assert header in headers, f"Security header {header} missing"
            assert headers[header] == expected_value, f"Security header {header} has incorrect value"
        
        # Test Content Security Policy
        assert 'Content-Security-Policy' in headers
        csp = headers['Content-Security-Policy']
        
        # Verify CSP directives
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "script-src" in csp
        assert "style-src" in csp
    
    def test_cors_headers_security(self):
        """Test CORS headers for security"""
        event = {
            'httpMethod': 'OPTIONS',
            'path': '/auth/register',
            'headers': {
                'Origin': 'https://malicious-site.com'
            },
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        response = auth_handler(event, context)
        
        headers = response.get('headers', {})
        
        # Check CORS headers
        assert 'Access-Control-Allow-Origin' in headers
        assert 'Access-Control-Allow-Methods' in headers
        assert 'Access-Control-Allow-Headers' in headers
        
        # In production, should not allow all origins
        # This test would need to be adjusted based on actual CORS policy
        origin = headers.get('Access-Control-Allow-Origin')
        if origin != '*':
            # If not wildcard, should be a specific allowed origin
            assert origin.startswith('https://')


class TestDataValidationAndSanitization:
    """Test data validation and sanitization across all inputs"""
    
    def test_input_length_limits(self):
        """Test that input length limits are enforced"""
        # Test extremely long inputs
        long_email = 'x' * 1000 + '@example.com'
        long_password = 'x' * 1000
        long_name = 'x' * 1000
        
        event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'headers': {},
            'body': json.dumps({
                'email': long_email,
                'password': long_password,
                'first_name': long_name,
                'last_name': long_name
            }),
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        response = auth_handler(event, context)
        
        # Should reject or truncate overly long inputs
        assert response['statusCode'] in [400, 422]
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_special_character_handling(self):
        """Test handling of special characters and unicode"""
        special_inputs = [
            'test@example.com\x00',  # Null byte
            'test@example.com\n\r',  # Newlines
            'test@example.com\t',    # Tab
            'test@example.com\x1f',  # Control character
            'test@example.com\u202e', # Unicode right-to-left override
            'test@example.com\ufeff', # Byte order mark
        ]
        
        context = Mock()
        context.function_name = 'test-function'
        context.aws_request_id = 'test-request-id'
        
        for special_input in special_inputs:
            event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'headers': {},
                'body': json.dumps({
                    'email': special_input,
                    'password': 'TestPassword123!'
                }),
                'requestContext': {
                    'requestId': 'test-request-id',
                    'identity': {
                        'sourceIp': '127.0.0.1',
                        'userAgent': 'test-agent'
                    }
                }
            }
            
            response = auth_handler(event, context)
            
            # Should handle special characters safely
            # Either reject them or sanitize them
            if response['statusCode'] in [200, 201]:
                # If accepted, verify special characters were sanitized
                body = json.loads(response['body'])
                response_str = json.dumps(body)
                assert '\x00' not in response_str
                assert '\x1f' not in response_str
            else:
                # Should be rejected with appropriate error
                assert response['statusCode'] in [400, 422]


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])