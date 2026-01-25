"""
Test security controls functionality
"""
import pytest
import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.auth.handler import lambda_handler
from shared.database import get_db_connection


def cleanup_test_data():
    """Clean up test data from security tables"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auth_rate_limits WHERE identifier LIKE 'test_%'")
            cursor.execute("DELETE FROM account_lockouts WHERE email LIKE 'test_%'")
            cursor.execute("DELETE FROM auth_audit_log WHERE email LIKE 'test_%'")
            cursor.execute("DELETE FROM users WHERE email LIKE 'test_%'")
            conn.commit()
            cursor.close()
    except Exception:
        pass


def test_rate_limiting():
    """Test rate limiting functionality"""
    cleanup_test_data()
    
    try:
        # Make multiple failed login attempts to trigger rate limiting
        for i in range(6):  # Exceed the email rate limit (5)
            event = {
                'httpMethod': 'POST',
                'path': '/auth/login',
                'body': json.dumps({
                    'email': 'test_rate_limit@example.com',
                    'password': 'WrongPassword123!'
                }),
                'headers': {
                    'X-Forwarded-For': '192.168.1.100',
                    'User-Agent': 'Test-Agent'
                }
            }
            
            response = lambda_handler(event, {})
            
            if i < 5:
                # First 5 attempts should return 401 (invalid credentials)
                assert response['statusCode'] == 401
            else:
                # 6th attempt should be rate limited
                assert response['statusCode'] == 429
                body = json.loads(response['body'])
                assert 'too many' in body['error'].lower()
                
    finally:
        cleanup_test_data()


def test_account_lockout():
    """Test account lockout functionality"""
    cleanup_test_data()
    
    try:
        # First register a user
        register_event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'body': json.dumps({
                'email': 'test_lockout@example.com',
                'password': 'ValidPass123!',
                'first_name': 'Test',
                'last_name': 'User'
            }),
            'headers': {
                'X-Forwarded-For': '192.168.1.101',
                'User-Agent': 'Test-Agent'
            }
        }
        
        register_response = lambda_handler(register_event, {})
        assert register_response['statusCode'] == 201
        
        # Make multiple failed login attempts to trigger account lockout
        for i in range(6):  # Exceed the failed attempts limit (5)
            login_event = {
                'httpMethod': 'POST',
                'path': '/auth/login',
                'body': json.dumps({
                    'email': 'test_lockout@example.com',
                    'password': 'WrongPassword123!'
                }),
                'headers': {
                    'X-Forwarded-For': '192.168.1.101',
                    'User-Agent': 'Test-Agent'
                }
            }
            
            response = lambda_handler(login_event, {})
            
            if i < 5:
                # First 5 attempts should return 401 (invalid credentials)
                assert response['statusCode'] == 401
            else:
                # 6th attempt should trigger account lockout
                assert response['statusCode'] == 423
                body = json.loads(response['body'])
                assert 'locked' in body['error'].lower()
                
    finally:
        cleanup_test_data()


def test_security_audit_logging():
    """Test that security events are logged"""
    cleanup_test_data()
    
    try:
        # Make a failed login attempt
        event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': 'test_audit@example.com',
                'password': 'WrongPassword123!'
            }),
            'headers': {
                'X-Forwarded-For': '192.168.1.102',
                'User-Agent': 'Test-Agent'
            }
        }
        
        response = lambda_handler(event, {})
        assert response['statusCode'] == 401
        
        # Check that the event was logged
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_type, email, ip_address, risk_score
                FROM auth_audit_log
                WHERE email = 'test_audit@example.com'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            assert result is not None
            
            event_type, email, ip_address, risk_score = result
            assert event_type == 'login_user_not_found'
            assert email == 'test_audit@example.com'
            assert str(ip_address) == '192.168.1.102'
            assert risk_score > 0
            
    finally:
        cleanup_test_data()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])