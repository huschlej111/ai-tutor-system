"""
Unit tests for auth_utils module
Tests password hashing, token management, and user extraction
"""
import pytest
import warnings
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.auth_utils import (
    hash_password,
    verify_password,
    hash_token,
    is_token_blacklisted,
    extract_user_from_cognito_event
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing functions"""
    
    def test_hash_password_creates_hash(self):
        """Test password hashing creates a valid hash"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            hashed = hash_password("TestPassword123!")
            
            assert hashed is not None
            assert len(hashed) > 0
            assert hashed != "TestPassword123!"
    
    def test_hash_password_different_each_time(self):
        """Test password hashing creates different hashes (salt)"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            hash1 = hash_password("TestPassword123!")
            hash2 = hash_password("TestPassword123!")
            
            assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """Test verifying correct password"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            password = "TestPassword123!"
            hashed = hash_password(password)
            
            assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            password = "TestPassword123!"
            hashed = hash_password(password)
            
            assert verify_password("WrongPassword", hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """Test verifying password with invalid hash"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert verify_password("password", "invalid_hash") is False


@pytest.mark.unit
class TestHashToken:
    """Test token hashing"""
    
    def test_hash_token_creates_hash(self):
        """Test token hashing creates a hash"""
        token = "test-token-123"
        hashed = hash_token(token)
        
        assert hashed is not None
        assert len(hashed) == 64  # SHA256 produces 64 hex characters
        assert hashed != token
    
    def test_hash_token_deterministic(self):
        """Test token hashing is deterministic"""
        token = "test-token-123"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        
        assert hash1 == hash2
    
    def test_hash_token_different_tokens(self):
        """Test different tokens produce different hashes"""
        hash1 = hash_token("token1")
        hash2 = hash_token("token2")
        
        assert hash1 != hash2


@pytest.mark.unit
class TestTokenBlacklist:
    """Test token blacklist checking"""
    
    @patch('shared.auth_utils.get_db_connection')
    def test_is_token_blacklisted_true(self, mock_db_conn):
        """Test checking if token is blacklisted"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_db_conn.return_value = mock_conn
        
        result = is_token_blacklisted("test-jti")
        assert result is True
    
    @patch('shared.auth_utils.get_db_connection')
    def test_is_token_blacklisted_false(self, mock_db_conn):
        """Test checking if token is not blacklisted"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_db_conn.return_value = mock_conn
        
        result = is_token_blacklisted("test-jti")
        assert result is False
    
    @patch('shared.auth_utils.get_db_connection')
    def test_is_token_blacklisted_db_error(self, mock_db_conn):
        """Test token blacklist check handles database errors gracefully"""
        mock_db_conn.side_effect = Exception("Database error")
        
        # Should return False on error to not break authentication
        result = is_token_blacklisted("test-jti")
        assert result is False


@pytest.mark.unit
class TestExtractUserFromCognitoEvent:
    """Test extracting user from Cognito-authorized events"""
    
    def test_extract_user_with_valid_claims(self):
        """Test extracting user from event with valid Cognito claims"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'test@example.com',
                        'cognito:username': 'testuser',
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        user_info = extract_user_from_cognito_event(event)
        
        assert user_info['valid'] is True
        assert user_info['user_id'] == 'user-123'
        assert user_info['email'] == 'test@example.com'
        assert user_info['username'] == 'testuser'
        assert user_info['email_verified'] is True
    
    def test_extract_user_email_not_verified(self):
        """Test extracting user with unverified email"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'test@example.com',
                        'cognito:username': 'testuser',
                        'email_verified': 'false'
                    }
                }
            }
        }
        
        user_info = extract_user_from_cognito_event(event)
        
        assert user_info['valid'] is True
        assert user_info['email_verified'] is False
    
    def test_extract_user_missing_claims(self):
        """Test extracting user when claims are missing"""
        event = {
            'requestContext': {
                'authorizer': {}
            }
        }
        
        user_info = extract_user_from_cognito_event(event)
        
        # Should return invalid unless in LocalStack environment
        if not os.environ.get('LOCALSTACK_ENDPOINT'):
            assert user_info['valid'] is False
            assert 'error' in user_info
    
    def test_extract_user_missing_request_context(self):
        """Test extracting user when request context is missing"""
        event = {}
        
        user_info = extract_user_from_cognito_event(event)
        
        # Should return invalid unless in LocalStack environment
        if not os.environ.get('LOCALSTACK_ENDPOINT'):
            assert user_info['valid'] is False
    
    @patch.dict(os.environ, {'LOCALSTACK_ENDPOINT': 'http://localhost:4566'})
    def test_extract_user_localstack_fallback(self):
        """Test LocalStack fallback when claims are missing"""
        event = {'requestContext': {'authorizer': {}}}
        
        user_info = extract_user_from_cognito_event(event)
        
        assert user_info['valid'] is True
        assert user_info['email'] == 'test@example.com'
