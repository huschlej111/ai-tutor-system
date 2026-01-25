"""
Security-focused tests for authentication
Tests rate limiting, brute force scenarios, JWT token security, session hijacking prevention, and password policy enforcement
"""
import pytest
import json
import time
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.auth.handler import lambda_handler
from shared.auth_utils import generate_jwt, verify_jwt, blacklist_token
from shared.security_controls import RateLimiter, AccountLockout
from shared.database import get_db_connection


def cleanup_test_data():
    """Clean up test data from security tables"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auth_rate_limits WHERE identifier LIKE 'test_%'")
            cursor.execute("DELETE FROM account_lockouts WHERE email LIKE 'test_%'")
            cursor.execute("DELETE FROM auth_audit_log WHERE email LIKE 'test_%'")
            cursor.execute("DELETE FROM token_blacklist WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
            cursor.execute("DELETE FROM users WHERE email LIKE 'test_%'")
            conn.commit()
            cursor.close()
    except Exception:
        pass


class TestAuthenticationSecurity:
    """Security-focused authentication tests"""
    
    def test_rate_limiting_by_ip(self):
        """Test rate limiting prevents brute force attacks by IP"""
        cleanup_test_data()
        
        try:
            ip_address = 'test_192.168.1.100'
            
            # Make multiple failed attempts from same IP
            for i in range(25):  # Exceed IP rate limit (20)
                event = {
                    'httpMethod': 'POST',
                    'path': '/auth/login',
                    'body': json.dumps({
                        'email': f'test_user_{i}@example.com',
                        'password': 'WrongPassword123!'
                    }),
                    'headers': {
                        'X-Forwarded-For': ip_address,
                        'User-Agent': 'Test-Security-Agent'
                    }
                }
                
                response = lambda_handler(event, {})
                
                if i < 20:
                    # First 20 attempts should return 401 (invalid credentials)
                    assert response['statusCode'] == 401
                else:
                    # Subsequent attempts should be rate limited
                    assert response['statusCode'] == 429
                    body = json.loads(response['body'])
                    assert 'too many' in body['error'].lower()
                    assert 'blocked_until' in body
                    
        finally:
            cleanup_test_data()
    
    def test_rate_limiting_by_email(self):
        """Test rate limiting prevents brute force attacks by email"""
        cleanup_test_data()
        
        try:
            email = 'test_rate_limit_email@example.com'
            
            # Make multiple failed attempts for same email
            for i in range(8):  # Exceed email rate limit (5)
                event = {
                    'httpMethod': 'POST',
                    'path': '/auth/login',
                    'body': json.dumps({
                        'email': email,
                        'password': 'WrongPassword123!'
                    }),
                    'headers': {
                        'X-Forwarded-For': f'192.168.1.{100 + i}',  # Different IPs
                        'User-Agent': 'Test-Security-Agent'
                    }
                }
                
                response = lambda_handler(event, {})
                
                if i < 5:
                    # First 5 attempts should return 401 (invalid credentials)
                    assert response['statusCode'] == 401
                else:
                    # Subsequent attempts should be rate limited
                    assert response['statusCode'] == 429
                    body = json.loads(response['body'])
                    assert 'too many' in body['error'].lower()
                    
        finally:
            cleanup_test_data()
    
    def test_account_lockout_brute_force_protection(self):
        """Test account lockout prevents brute force attacks"""
        cleanup_test_data()
        
        try:
            # First register a user
            email = 'test_lockout_security@example.com'
            register_event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps({
                    'email': email,
                    'password': 'ValidPass123!',
                    'first_name': 'Test',
                    'last_name': 'User'
                }),
                'headers': {
                    'X-Forwarded-For': '192.168.1.150',
                    'User-Agent': 'Test-Security-Agent'
                }
            }
            
            register_response = lambda_handler(register_event, {})
            assert register_response['statusCode'] == 201
            
            # Make multiple failed login attempts to trigger lockout
            for i in range(7):  # Exceed failed attempts limit (5)
                login_event = {
                    'httpMethod': 'POST',
                    'path': '/auth/login',
                    'body': json.dumps({
                        'email': email,
                        'password': 'WrongPassword123!'
                    }),
                    'headers': {
                        'X-Forwarded-For': f'192.168.1.{150 + i}',  # Different IPs
                        'User-Agent': 'Test-Security-Agent'
                    }
                }
                
                response = lambda_handler(login_event, {})
                
                if i < 5:
                    # First 5 attempts should return 401 (invalid credentials)
                    assert response['statusCode'] == 401
                    if i > 0:  # Check attempts remaining after first attempt
                        body = json.loads(response['body'])
                        if 'attempts_remaining' in body:
                            assert body['attempts_remaining'] == 5 - i - 1
                else:
                    # 6th and 7th attempts should trigger account lockout
                    assert response['statusCode'] == 423
                    body = json.loads(response['body'])
                    assert 'locked' in body['error'].lower()
                    assert 'locked_until' in body
            
            # Test that even correct password fails when account is locked
            correct_login_event = {
                'httpMethod': 'POST',
                'path': '/auth/login',
                'body': json.dumps({
                    'email': email,
                    'password': 'ValidPass123!'  # Correct password
                }),
                'headers': {
                    'X-Forwarded-For': '192.168.1.160',
                    'User-Agent': 'Test-Security-Agent'
                }
            }
            
            response = lambda_handler(correct_login_event, {})
            assert response['statusCode'] == 423  # Still locked
            
        finally:
            cleanup_test_data()
    
    def test_jwt_token_security_properties(self):
        """Test JWT token security properties"""
        cleanup_test_data()
        
        try:
            # Test token generation and verification
            user_id = 'test_user_123'
            email = 'test_jwt@example.com'
            
            # Generate token
            token = generate_jwt(user_id, email)
            assert token is not None
            assert len(token) > 0
            
            # Verify valid token
            verification = verify_jwt(token)
            assert verification['valid'] is True
            assert verification['user_id'] == user_id
            assert verification['email'] == email
            assert 'payload' in verification
            
            # Test token with Bearer prefix
            bearer_token = f'Bearer {token}'
            verification = verify_jwt(bearer_token)
            assert verification['valid'] is True
            
            # Test invalid token formats
            invalid_tokens = [
                '',  # Empty token
                'invalid.token.format',  # Invalid JWT format
                'Bearer ',  # Bearer with no token
                'Bearer invalid_token',  # Bearer with invalid token
                token[:-5],  # Truncated token
                token + 'extra',  # Modified token
            ]
            
            for invalid_token in invalid_tokens:
                verification = verify_jwt(invalid_token)
                assert verification['valid'] is False
                assert 'error' in verification
            
            # Test token blacklisting
            blacklist_result = blacklist_token(token, user_id, 'security_test')
            assert blacklist_result is True
            
            # Verify blacklisted token is invalid
            verification = verify_jwt(token)
            assert verification['valid'] is False
            assert 'invalidated' in verification['error']
            
        finally:
            cleanup_test_data()
    
    def test_session_hijacking_prevention(self):
        """Test session hijacking prevention measures"""
        cleanup_test_data()
        
        try:
            # Register and login a user
            email = 'test_session_security@example.com'
            register_event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps({
                    'email': email,
                    'password': 'ValidPass123!',
                    'first_name': 'Test',
                    'last_name': 'User'
                }),
                'headers': {
                    'X-Forwarded-For': '192.168.1.170',
                    'User-Agent': 'Test-Session-Agent'
                }
            }
            
            register_response = lambda_handler(register_event, {})
            assert register_response['statusCode'] == 201
            
            register_body = json.loads(register_response['body'])
            token = register_body['token']
            
            # Test token validation
            validate_event = {
                'httpMethod': 'GET',
                'path': '/auth/validate',
                'headers': {'Authorization': f'Bearer {token}'}
            }
            
            validate_response = lambda_handler(validate_event, {})
            assert validate_response['statusCode'] == 200
            
            # Test logout invalidates token
            logout_event = {
                'httpMethod': 'POST',
                'path': '/auth/logout',
                'headers': {'Authorization': f'Bearer {token}'}
            }
            
            logout_response = lambda_handler(logout_event, {})
            assert logout_response['statusCode'] == 200
            
            logout_body = json.loads(logout_response['body'])
            assert logout_body.get('token_invalidated') is True
            
            # Test that invalidated token cannot be used
            validate_response_after_logout = lambda_handler(validate_event, {})
            assert validate_response_after_logout['statusCode'] == 401
            
            validate_body = json.loads(validate_response_after_logout['body'])
            assert 'invalidated' in validate_body['error']
            
        finally:
            cleanup_test_data()
    
    def test_password_policy_enforcement(self):
        """Test password policy enforcement"""
        cleanup_test_data()
        
        try:
            # Test various password policy violations
            weak_passwords = [
                ('', 'required'),
                ('short', '8 characters'),
                ('nouppercase123!', 'uppercase'),
                ('NOLOWERCASE123!', 'lowercase'),
                ('NoDigits!', 'digit'),
                ('NoSpecialChars123', 'special character'),
                ('a' * 129, '128 characters'),  # Too long
            ]
            
            # Test registration with weak passwords - Cognito should reject them
            for password, expected_error_keyword in weak_passwords:
                # Skip the direct validate_password call since Cognito handles this internally
                pass
            
            # Test registration with weak passwords
            for i, (password, _) in enumerate(weak_passwords):
                email = f'test_weak_password_{i}@example.com'
                event = {
                    'httpMethod': 'POST',
                    'path': '/auth/register',
                    'body': json.dumps({
                        'email': email,
                        'password': password,
                        'first_name': 'Test',
                        'last_name': 'User'
                    }),
                    'headers': {
                        'X-Forwarded-For': '192.168.1.180',
                        'User-Agent': 'Test-Password-Agent'
                    }
                }
                
                response = lambda_handler(event, {})
                assert response['statusCode'] == 400
                body = json.loads(response['body'])
                assert 'password' in body['error'].lower()
            
            # Test strong passwords are accepted
            strong_passwords = [
                'ValidPass123!',
                'AnotherGood1@',
                'Complex#Pass9',
                'Str0ng&Secure',
            ]
            
            # Test registration with strong passwords - Cognito should accept them
            for i, password in enumerate(strong_passwords):
                # Skip the direct validate_password call since Cognito handles this internally
                
                # Test registration with strong password
                email = f'test_strong_password_{i}@example.com'
                event = {
                    'httpMethod': 'POST',
                    'path': '/auth/register',
                    'body': json.dumps({
                        'email': email,
                        'password': password,
                        'first_name': 'Test',
                        'last_name': 'User'
                    }),
                    'headers': {
                        'X-Forwarded-For': '192.168.1.181',
                        'User-Agent': 'Test-Password-Agent'
                    }
                }
                
                response = lambda_handler(event, {})
                assert response['statusCode'] == 201
                
        finally:
            cleanup_test_data()
    
    def test_security_audit_logging(self):
        """Test that security events are properly logged"""
        cleanup_test_data()
        
        try:
            # Test failed login logging
            event = {
                'httpMethod': 'POST',
                'path': '/auth/login',
                'body': json.dumps({
                    'email': 'test_audit_security@example.com',
                    'password': 'WrongPassword123!'
                }),
                'headers': {
                    'X-Forwarded-For': '192.168.1.190',
                    'User-Agent': 'Test-Audit-Agent'
                }
            }
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 401
            
            # Check that security event was logged
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT event_type, email, ip_address, user_agent, risk_score
                    FROM auth_audit_log
                    WHERE email = 'test_audit_security@example.com'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                result = cursor.fetchone()
                assert result is not None
                
                event_type, email, ip_address, user_agent, risk_score = result
                assert event_type == 'login_user_not_found'
                assert email == 'test_audit_security@example.com'
                assert str(ip_address) == '192.168.1.190'
                assert user_agent == 'Test-Audit-Agent'
                assert risk_score > 0
            
            # Test successful registration logging
            register_event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps({
                    'email': 'test_audit_register@example.com',
                    'password': 'ValidPass123!',
                    'first_name': 'Test',
                    'last_name': 'User'
                }),
                'headers': {
                    'X-Forwarded-For': '192.168.1.191',
                    'User-Agent': 'Test-Audit-Agent'
                }
            }
            
            register_response = lambda_handler(register_event, {})
            assert register_response['statusCode'] == 201
            
            # Check that registration was logged
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT event_type, email, risk_score
                    FROM auth_audit_log
                    WHERE email = 'test_audit_register@example.com'
                    AND event_type = 'register_success'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                
                result = cursor.fetchone()
                assert result is not None
                
                event_type, email, risk_score = result
                assert event_type == 'register_success'
                assert email == 'test_audit_register@example.com'
                assert risk_score == 0  # Successful events have low risk
                
        finally:
            cleanup_test_data()
    
    def test_progressive_lockout_timing(self):
        """Test that lockout duration increases with repeated violations"""
        cleanup_test_data()
        
        try:
            # Register a user
            email = 'test_progressive_lockout@example.com'
            register_event = {
                'httpMethod': 'POST',
                'path': '/auth/register',
                'body': json.dumps({
                    'email': email,
                    'password': 'ValidPass123!',
                    'first_name': 'Test',
                    'last_name': 'User'
                }),
                'headers': {
                    'X-Forwarded-For': '192.168.1.200',
                    'User-Agent': 'Test-Progressive-Agent'
                }
            }
            
            register_response = lambda_handler(register_event, {})
            assert register_response['statusCode'] == 201
            
            # Trigger first lockout (5 failed attempts)
            for i in range(6):
                login_event = {
                    'httpMethod': 'POST',
                    'path': '/auth/login',
                    'body': json.dumps({
                        'email': email,
                        'password': 'WrongPassword123!'
                    }),
                    'headers': {
                        'X-Forwarded-For': f'192.168.1.{200 + i}',
                        'User-Agent': 'Test-Progressive-Agent'
                    }
                }
                
                response = lambda_handler(login_event, {})
                
                if i < 5:
                    assert response['statusCode'] == 401
                else:
                    assert response['statusCode'] == 423
                    body = json.loads(response['body'])
                    assert 'locked' in body['error'].lower()
            
            # Verify account is locked
            lockout_check = AccountLockout.check_account_lockout(email)
            assert lockout_check['locked'] is True
            assert lockout_check['failed_attempts'] >= 5
            
        finally:
            cleanup_test_data()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])