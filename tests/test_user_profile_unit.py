"""
Unit tests for user_profile Lambda handler
Tests profile retrieval and updates
"""
import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.mark.unit
@patch('lambda_functions.user_profile.handler.db_proxy')
class TestUserProfileHandler:
    """Test user profile Lambda handler"""
    
    def test_get_profile_success(self, mock_db_proxy):
        """Test successfully getting user profile"""
        from lambda_functions.user_profile.handler import lambda_handler
        
        mock_db_proxy.execute_query.return_value = [{
            'id': 'user-123',
            'cognito_sub': 'cognito-123',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True,
            'created_at': '2024-01-01',
            'updated_at': '2024-01-01',
            'last_login': '2024-01-02'
        }]
        
        event = {
            'httpMethod': 'GET',
            'requestContext': {
                'authorizer': {
                    'claims': {'sub': 'cognito-123'}
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['data']['email'] == 'test@example.com'
    
    def test_get_profile_not_found(self, mock_db_proxy):
        """Test getting profile when user not found"""
        from lambda_functions.user_profile.handler import lambda_handler
        
        mock_db_proxy.execute_query.return_value = []
        
        event = {
            'httpMethod': 'GET',
            'requestContext': {
                'authorizer': {
                    'claims': {'sub': 'nonexistent'}
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 404
    
    def test_get_profile_unauthorized(self, mock_db_proxy):
        """Test getting profile without authentication"""
        from lambda_functions.user_profile.handler import lambda_handler
        
        event = {
            'httpMethod': 'GET',
            'requestContext': {}
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 401
    
    def test_unsupported_method(self, mock_db_proxy):
        """Test unsupported HTTP method"""
        from lambda_functions.user_profile.handler import lambda_handler
        
        event = {
            'httpMethod': 'DELETE',
            'requestContext': {
                'authorizer': {
                    'claims': {'sub': 'cognito-123'}
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 405
