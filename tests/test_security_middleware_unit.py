"""
Unit tests for security_middleware module
Tests security middleware functions
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.mark.unit
class TestSecurityMiddleware:
    """Test security middleware"""
    
    def test_sanitize_input(self):
        """Test input sanitization"""
        from shared.security_middleware import sanitize_input
        
        dirty_input = "<script>alert('xss')</script>Hello"
        clean = sanitize_input(dirty_input)
        
        assert '<script>' not in clean
        assert 'Hello' in clean
    
    def test_validate_request_headers(self):
        """Test request header validation"""
        from shared.security_middleware import validate_headers
        
        valid_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
        
        assert validate_headers(valid_headers) is True
    
    def test_rate_limit_check(self):
        """Test rate limiting"""
        from shared.security_middleware import check_rate_limit
        
        # Mock rate limit check
        result = check_rate_limit('user-123', limit=100)
        assert isinstance(result, bool)
    
    def test_validate_cors_origin(self):
        """Test CORS origin validation"""
        from shared.security_middleware import validate_cors_origin
        
        allowed_origin = 'https://example.com'
        assert validate_cors_origin(allowed_origin) is True
        
        blocked_origin = 'https://malicious.com'
        assert validate_cors_origin(blocked_origin) is False
