"""
Test security monitoring functionality
"""
import pytest
import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.auth.handler import lambda_handler
from shared.security_monitoring import SecurityMonitor, SecurityReporting
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


def test_suspicious_activity_detection():
    """Test detection of suspicious activity patterns"""
    cleanup_test_data()
    
    try:
        # Generate multiple failed login attempts to create suspicious pattern
        for i in range(8):
            event = {
                'httpMethod': 'POST',
                'path': '/auth/login',
                'body': json.dumps({
                    'email': 'test_suspicious@example.com',
                    'password': 'WrongPassword123!'
                }),
                'headers': {
                    'X-Forwarded-For': f'192.168.1.{100 + i}',  # Different IPs
                    'User-Agent': f'Test-Agent-{i % 3}'  # Different user agents
                }
            }
            
            response = lambda_handler(event, {})
            # Should be 401 for invalid credentials or 429 for rate limiting
            assert response['statusCode'] in [401, 429]
        
        # Analyze suspicious activity
        analysis = SecurityMonitor.detect_suspicious_activity('test_suspicious@example.com')
        
        assert analysis['suspicious'] is True
        assert len(analysis['patterns']) > 0
        
        # Should detect multiple patterns
        pattern_types = [p['type'] for p in analysis['patterns']]
        assert 'excessive_failed_logins' in pattern_types
        assert 'multiple_ip_addresses' in pattern_types
        
    finally:
        cleanup_test_data()


def test_security_alert_generation():
    """Test security alert generation"""
    cleanup_test_data()
    
    try:
        # Generate a security alert
        alert = SecurityMonitor.generate_security_alert(
            'test_alert',
            'test_alert@example.com',
            'high',
            {'test_detail': 'test_value'},
            'test_user_id'
        )
        
        assert alert['alert_type'] == 'test_alert'
        assert alert['severity'] == 'high'
        assert alert['email'] == 'test_alert@example.com'
        assert alert['user_id'] == 'test_user_id'
        assert 'alert_id' in alert
        assert 'recommended_actions' in alert
        assert len(alert['recommended_actions']) > 0
        
    finally:
        cleanup_test_data()


def test_security_monitoring_basic():
    """Test basic security monitoring functionality"""
    cleanup_test_data()
    
    try:
        # Test alert generation
        alert = SecurityMonitor.generate_security_alert(
            'test_alert',
            'test_basic@example.com',
            'medium',
            {'test': 'data'}
        )
        
        assert alert['alert_type'] == 'test_alert'
        assert alert['severity'] == 'medium'
        assert 'alert_id' in alert
        assert 'recommended_actions' in alert
        
        # Test suspicious activity detection with no data
        analysis = SecurityMonitor.detect_suspicious_activity('nonexistent@example.com')
        assert analysis['suspicious'] is False
        assert analysis['patterns'] == []
        
    finally:
        cleanup_test_data()


def test_compliance_audit_trail():
    """Test compliance audit trail generation"""
    cleanup_test_data()
    
    try:
        # Generate some test activity
        event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': 'test_audit_trail@example.com',
                'password': 'WrongPassword123!'
            }),
            'headers': {
                'X-Forwarded-For': '192.168.1.201',
                'User-Agent': 'Test-Audit-Agent'
            }
        }
        
        response = lambda_handler(event, {})
        assert response['statusCode'] == 401
        
        # Get audit trail
        audit_trail = SecurityReporting.get_compliance_audit_trail(
            'test_audit_trail@example.com', 
            days=1
        )
        
        assert len(audit_trail) > 0
        
        # Check audit trail structure
        event_record = audit_trail[0]
        assert 'event_type' in event_record
        assert 'ip_address' in event_record
        assert 'user_agent' in event_record
        assert 'risk_score' in event_record
        assert 'timestamp' in event_record
        
    finally:
        cleanup_test_data()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])