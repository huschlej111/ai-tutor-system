"""
Authorization utilities for role-based access control
Handles Cognito group-based authorization and API access control
"""
import json
import boto3
import os
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError


# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Get Cognito configuration from environment
USER_POOL_ID = os.environ.get('USER_POOL_ID')


class AuthorizationError(Exception):
    """Custom exception for authorization errors"""
    pass


def extract_user_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user information from API Gateway event with Cognito authorizer
    """
    try:
        # Get user info from Cognito authorizer context
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        # Extract claims from Cognito JWT
        claims = authorizer.get('claims', {})
        
        if not claims:
            raise AuthorizationError("No user claims found in request context")
        
        return {
            'user_id': claims.get('sub'),
            'email': claims.get('email'),
            'username': claims.get('cognito:username'),
            'groups': claims.get('cognito:groups', '').split(',') if claims.get('cognito:groups') else [],
            'token_use': claims.get('token_use'),
            'auth_time': claims.get('auth_time'),
            'iss': claims.get('iss'),
            'exp': claims.get('exp')
        }
        
    except Exception as e:
        raise AuthorizationError(f"Failed to extract user from event: {str(e)}")


def get_user_groups(user_id: str) -> List[str]:
    """
    Get user groups from Cognito User Pool
    """
    try:
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
        
        return [group['GroupName'] for group in response.get('Groups', [])]
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            return []
        else:
            raise AuthorizationError(f"Failed to get user groups: {e.response['Error']['Message']}")
    except Exception as e:
        raise AuthorizationError(f"Failed to get user groups: {str(e)}")


def check_user_permission(user_info: Dict[str, Any], required_groups: List[str]) -> bool:
    """
    Check if user has required group membership for access
    """
    user_groups = user_info.get('groups', [])
    
    # Admin group has access to everything
    if 'admin' in user_groups:
        return True
    
    # Check if user has any of the required groups
    return any(group in user_groups for group in required_groups)


def require_groups(required_groups: List[str]):
    """
    Decorator to require specific Cognito groups for Lambda function access
    """
    def decorator(func):
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            try:
                # Extract user information
                user_info = extract_user_from_event(event)
                
                # Check permissions
                if not check_user_permission(user_info, required_groups):
                    return {
                        'statusCode': 403,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                        },
                        'body': json.dumps({
                            'error': 'Forbidden',
                            'message': f'Access denied. Required groups: {", ".join(required_groups)}'
                        })
                    }
                
                # Add user info to event for use in function
                event['user_info'] = user_info
                
                # Call the original function
                return func(event, context)
                
            except AuthorizationError as e:
                return {
                    'statusCode': 401,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                    },
                    'body': json.dumps({
                        'error': 'Unauthorized',
                        'message': str(e)
                    })
                }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                    },
                    'body': json.dumps({
                        'error': 'Internal Server Error',
                        'message': 'An unexpected error occurred'
                    })
                }
        
        return wrapper
    return decorator


def require_admin(func):
    """
    Decorator to require admin group access
    """
    return require_groups(['admin'])(func)


def require_instructor_or_admin(func):
    """
    Decorator to require instructor or admin group access
    """
    return require_groups(['instructor', 'admin'])(func)


def require_authenticated(func):
    """
    Decorator to require any authenticated user (any group)
    """
    return require_groups(['student', 'instructor', 'admin'])(func)


def add_user_to_group(user_id: str, group_name: str) -> bool:
    """
    Add user to a Cognito User Pool group
    """
    try:
        cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=user_id,
            GroupName=group_name
        )
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            raise AuthorizationError(f"User {user_id} not found")
        elif error_code == 'ResourceNotFoundException':
            raise AuthorizationError(f"Group {group_name} not found")
        else:
            raise AuthorizationError(f"Failed to add user to group: {e.response['Error']['Message']}")
    except Exception as e:
        raise AuthorizationError(f"Failed to add user to group: {str(e)}")


def remove_user_from_group(user_id: str, group_name: str) -> bool:
    """
    Remove user from a Cognito User Pool group
    """
    try:
        cognito_client.admin_remove_user_from_group(
            UserPoolId=USER_POOL_ID,
            Username=user_id,
            GroupName=group_name
        )
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'UserNotFoundException':
            raise AuthorizationError(f"User {user_id} not found")
        elif error_code == 'ResourceNotFoundException':
            raise AuthorizationError(f"Group {group_name} not found")
        else:
            raise AuthorizationError(f"Failed to remove user from group: {e.response['Error']['Message']}")
    except Exception as e:
        raise AuthorizationError(f"Failed to remove user from group: {str(e)}")


def get_api_rate_limit_for_user(user_groups: List[str]) -> Dict[str, int]:
    """
    Get appropriate rate limits based on user groups
    """
    if 'admin' in user_groups:
        return {
            'rate_limit': 500,
            'burst_limit': 1000,
            'daily_quota': 10000
        }
    elif 'instructor' in user_groups:
        return {
            'rate_limit': 200,
            'burst_limit': 400,
            'daily_quota': 5000
        }
    else:  # student or default
        return {
            'rate_limit': 100,
            'burst_limit': 200,
            'daily_quota': 1000
        }


def validate_api_access(event: Dict[str, Any], required_permissions: List[str]) -> Dict[str, Any]:
    """
    Validate API access based on user groups and required permissions
    Returns user info if authorized, raises AuthorizationError if not
    """
    try:
        # Extract user information
        user_info = extract_user_from_event(event)
        
        # Check if user has required permissions
        user_groups = user_info.get('groups', [])
        
        # Admin has access to everything
        if 'admin' in user_groups:
            return user_info
        
        # Check specific permissions
        for permission in required_permissions:
            if permission == 'batch_upload' and 'instructor' not in user_groups and 'admin' not in user_groups:
                raise AuthorizationError("Batch upload requires instructor or admin privileges")
            elif permission == 'user_management' and 'admin' not in user_groups:
                raise AuthorizationError("User management requires admin privileges")
            elif permission == 'content_moderation' and 'instructor' not in user_groups and 'admin' not in user_groups:
                raise AuthorizationError("Content moderation requires instructor or admin privileges")
        
        return user_info
        
    except AuthorizationError:
        raise
    except Exception as e:
        raise AuthorizationError(f"Failed to validate API access: {str(e)}")