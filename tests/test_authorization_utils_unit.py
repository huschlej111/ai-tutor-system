"""
Unit tests for authorization_utils module
Tests role-based access control and Cognito group authorization
"""
import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.authorization_utils import (
    extract_user_from_event,
    get_user_groups,
    check_user_permission,
    require_groups,
    require_admin,
    require_authenticated,
    add_user_to_group,
    remove_user_from_group,
    get_api_rate_limit_for_user,
    validate_api_access,
    AuthorizationError
)


@pytest.mark.unit
class TestExtractUserFromEvent:
    """Test user extraction from API Gateway events"""
    
    def test_extract_user_with_valid_claims(self):
        """Test extracting user from event with valid Cognito claims"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'test@example.com',
                        'cognito:username': 'testuser',
                        'cognito:groups': 'student,instructor',
                        'token_use': 'access',
                        'auth_time': '1234567890',
                        'iss': 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test',
                        'exp': '1234567890'
                    }
                }
            }
        }
        
        user_info = extract_user_from_event(event)
        
        assert user_info['user_id'] == 'user-123'
        assert user_info['email'] == 'test@example.com'
        assert user_info['username'] == 'testuser'
        assert user_info['groups'] == ['student', 'instructor']
    
    def test_extract_user_without_groups(self):
        """Test extracting user without groups"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'test@example.com'
                    }
                }
            }
        }
        
        user_info = extract_user_from_event(event)
        assert user_info['groups'] == []
    
    def test_extract_user_missing_claims(self):
        """Test error when claims are missing"""
        event = {'requestContext': {'authorizer': {}}}
        
        with pytest.raises(AuthorizationError, match="No user claims found"):
            extract_user_from_event(event)
    
    def test_extract_user_missing_request_context(self):
        """Test error when request context is missing"""
        event = {}
        
        with pytest.raises(AuthorizationError):
            extract_user_from_event(event)


@pytest.mark.unit
class TestGetUserGroups:
    """Test getting user groups from Cognito"""
    
    @patch('shared.authorization_utils.cognito_client')
    def test_get_user_groups_success(self, mock_cognito):
        """Test successfully getting user groups"""
        mock_cognito.admin_list_groups_for_user.return_value = {
            'Groups': [
                {'GroupName': 'student'},
                {'GroupName': 'instructor'}
            ]
        }
        
        groups = get_user_groups('user-123')
        
        assert groups == ['student', 'instructor']
        mock_cognito.admin_list_groups_for_user.assert_called_once()
    
    @patch('shared.authorization_utils.cognito_client')
    def test_get_user_groups_user_not_found(self, mock_cognito):
        """Test handling user not found"""
        from botocore.exceptions import ClientError
        mock_cognito.admin_list_groups_for_user.side_effect = ClientError(
            {'Error': {'Code': 'UserNotFoundException', 'Message': 'User not found'}},
            'admin_list_groups_for_user'
        )
        
        groups = get_user_groups('nonexistent-user')
        assert groups == []
    
    @patch('shared.authorization_utils.cognito_client')
    def test_get_user_groups_other_error(self, mock_cognito):
        """Test handling other Cognito errors"""
        from botocore.exceptions import ClientError
        mock_cognito.admin_list_groups_for_user.side_effect = ClientError(
            {'Error': {'Code': 'InternalError', 'Message': 'Internal error'}},
            'admin_list_groups_for_user'
        )
        
        with pytest.raises(AuthorizationError, match="Failed to get user groups"):
            get_user_groups('user-123')


@pytest.mark.unit
class TestCheckUserPermission:
    """Test permission checking logic"""
    
    def test_admin_has_all_permissions(self):
        """Test that admin group has access to everything"""
        user_info = {'groups': ['admin']}
        
        assert check_user_permission(user_info, ['student'])
        assert check_user_permission(user_info, ['instructor'])
        assert check_user_permission(user_info, ['any_group'])
    
    def test_user_with_required_group(self):
        """Test user with required group has permission"""
        user_info = {'groups': ['student', 'instructor']}
        
        assert check_user_permission(user_info, ['instructor'])
        assert check_user_permission(user_info, ['student'])
    
    def test_user_without_required_group(self):
        """Test user without required group is denied"""
        user_info = {'groups': ['student']}
        
        assert not check_user_permission(user_info, ['instructor'])
        assert not check_user_permission(user_info, ['admin'])
    
    def test_user_with_no_groups(self):
        """Test user with no groups is denied"""
        user_info = {'groups': []}
        
        assert not check_user_permission(user_info, ['student'])


@pytest.mark.unit
class TestRequireGroupsDecorator:
    """Test require_groups decorator"""
    
    def test_authorized_user_passes(self):
        """Test authorized user can access function"""
        @require_groups(['student'])
        def test_function(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'test@example.com',
                        'cognito:groups': 'student'
                    }
                }
            }
        }
        
        response = test_function(event, None)
        assert response['statusCode'] == 200
    
    def test_unauthorized_user_denied(self):
        """Test unauthorized user is denied"""
        @require_groups(['admin'])
        def test_function(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'email': 'test@example.com',
                        'cognito:groups': 'student'
                    }
                }
            }
        }
        
        response = test_function(event, None)
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Forbidden' in body['error']
    
    def test_missing_claims_returns_401(self):
        """Test missing claims returns 401"""
        @require_groups(['student'])
        def test_function(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {'requestContext': {}}
        
        response = test_function(event, None)
        assert response['statusCode'] == 401


@pytest.mark.unit
class TestAddRemoveUserFromGroup:
    """Test adding/removing users from groups"""
    
    @patch('shared.authorization_utils.cognito_client')
    def test_add_user_to_group_success(self, mock_cognito):
        """Test successfully adding user to group"""
        mock_cognito.admin_add_user_to_group.return_value = {}
        
        result = add_user_to_group('user-123', 'instructor')
        assert result is True
    
    @patch('shared.authorization_utils.cognito_client')
    def test_add_user_to_group_user_not_found(self, mock_cognito):
        """Test error when user not found"""
        from botocore.exceptions import ClientError
        mock_cognito.admin_add_user_to_group.side_effect = ClientError(
            {'Error': {'Code': 'UserNotFoundException', 'Message': 'User not found'}},
            'admin_add_user_to_group'
        )
        
        with pytest.raises(AuthorizationError, match="User .* not found"):
            add_user_to_group('nonexistent', 'instructor')
    
    @patch('shared.authorization_utils.cognito_client')
    def test_remove_user_from_group_success(self, mock_cognito):
        """Test successfully removing user from group"""
        mock_cognito.admin_remove_user_from_group.return_value = {}
        
        result = remove_user_from_group('user-123', 'instructor')
        assert result is True


@pytest.mark.unit
class TestGetApiRateLimitForUser:
    """Test rate limit calculation based on user groups"""
    
    def test_admin_rate_limits(self):
        """Test admin gets highest rate limits"""
        limits = get_api_rate_limit_for_user(['admin'])
        
        assert limits['rate_limit'] == 500
        assert limits['burst_limit'] == 1000
        assert limits['daily_quota'] == 10000
    
    def test_instructor_rate_limits(self):
        """Test instructor gets medium rate limits"""
        limits = get_api_rate_limit_for_user(['instructor'])
        
        assert limits['rate_limit'] == 200
        assert limits['burst_limit'] == 400
        assert limits['daily_quota'] == 5000
    
    def test_student_rate_limits(self):
        """Test student gets standard rate limits"""
        limits = get_api_rate_limit_for_user(['student'])
        
        assert limits['rate_limit'] == 100
        assert limits['burst_limit'] == 200
        assert limits['daily_quota'] == 1000
    
    def test_no_groups_gets_default_limits(self):
        """Test user with no groups gets default limits"""
        limits = get_api_rate_limit_for_user([])
        
        assert limits['rate_limit'] == 100


@pytest.mark.unit
class TestValidateApiAccess:
    """Test API access validation"""
    
    def test_admin_has_all_permissions(self):
        """Test admin can access all APIs"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'admin-123',
                        'email': 'admin@example.com',
                        'cognito:groups': 'admin'
                    }
                }
            }
        }
        
        user_info = validate_api_access(event, ['batch_upload', 'user_management'])
        assert user_info['user_id'] == 'admin-123'
    
    def test_instructor_can_batch_upload(self):
        """Test instructor can access batch upload"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'instructor-123',
                        'email': 'instructor@example.com',
                        'cognito:groups': 'instructor'
                    }
                }
            }
        }
        
        user_info = validate_api_access(event, ['batch_upload'])
        assert user_info['user_id'] == 'instructor-123'
    
    def test_student_cannot_batch_upload(self):
        """Test student cannot access batch upload"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'student-123',
                        'email': 'student@example.com',
                        'cognito:groups': 'student'
                    }
                }
            }
        }
        
        with pytest.raises(AuthorizationError, match="Batch upload requires"):
            validate_api_access(event, ['batch_upload'])
    
    def test_non_admin_cannot_manage_users(self):
        """Test non-admin cannot manage users"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'instructor-123',
                        'email': 'instructor@example.com',
                        'cognito:groups': 'instructor'
                    }
                }
            }
        }
        
        with pytest.raises(AuthorizationError, match="User management requires admin"):
            validate_api_access(event, ['user_management'])
