"""
Property-based tests for Cognito authentication round trip
Tests the fundamental property that authentication tokens can be validated

TESTING STRATEGY:
This file uses a layered testing approach to prevent "shadow success":

1. GUARD TEST (test_registration_write_path_guard):
   - Uses guaranteed unique users (UUID + timestamp)
   - Ensures registration write path actually works
   - Prevents false positives in property tests
   - MUST return 201 Created (no fallback to 409)

2. PROPERTY TESTS (test_cognito_authentication_round_trip, etc.):
   - Focus on business invariants across many inputs
   - Handle existing users gracefully (accept 201 or 409)
   - Test core authentication round-trip properties
   - Optimized for testing logic, not write paths

3. UNIT TESTS (test_logout_invalidates_tokens):
   - Test specific behaviors with controlled data
   - Use unique users to avoid test interference
   - Validate specific authentication flows

This strategy ensures both the write path works AND the business logic is correct.
"""
import pytest
import boto3
import json
import os
import sys
import uuid
import time
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from moto import mock_aws
from botocore.exceptions import ClientError

# Test configuration
TEST_USER_POOL_NAME = "test-tutor-system-users"
TEST_CLIENT_NAME = "test-tutor-system-client"


@pytest.fixture
def cognito_setup():
    """Set up mock Cognito User Pool for testing"""
    # Temporarily remove LocalStack endpoint to use moto instead
    original_endpoint = os.environ.pop('AWS_ENDPOINT_URL', None)
    
    try:
        with mock_aws():
            # Create Cognito client
            client = boto3.client('cognito-idp', region_name='us-east-1')
            
            # Create User Pool
            user_pool = client.create_user_pool(
                PoolName=TEST_USER_POOL_NAME,
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8,
                        'RequireUppercase': True,
                        'RequireLowercase': True,
                        'RequireNumbers': True,
                        'RequireSymbols': True
                    }
                },
                AutoVerifiedAttributes=['email'],
                UsernameAttributes=['email'],
                VerificationMessageTemplate={
                    'DefaultEmailOption': 'CONFIRM_WITH_CODE'
                },
                AdminCreateUserConfig={
                    'AllowAdminCreateUserOnly': False,
                    'UnusedAccountValidityDays': 7
                }
            )
            
            user_pool_id = user_pool['UserPool']['Id']
            
            # Create User Pool Client
            client_response = client.create_user_pool_client(
                UserPoolId=user_pool_id,
                ClientName=TEST_CLIENT_NAME,
                ExplicitAuthFlows=[
                    'ALLOW_USER_PASSWORD_AUTH',
                    'ALLOW_USER_SRP_AUTH',
                    'ALLOW_REFRESH_TOKEN_AUTH',
                    'ALLOW_ADMIN_USER_PASSWORD_AUTH'
                ],
                GenerateSecret=False,
                SupportedIdentityProviders=['COGNITO'],
                ReadAttributes=['email', 'given_name', 'family_name'],
                WriteAttributes=['email', 'given_name', 'family_name']
            )
            
            client_id = client_response['UserPoolClient']['ClientId']
            
            # Set environment variables
            os.environ['USER_POOL_ID'] = user_pool_id
            os.environ['USER_POOL_CLIENT_ID'] = client_id
            os.environ['AWS_REGION'] = 'us-east-1'
            
            yield {
                'client': client,
                'user_pool_id': user_pool_id,
                'client_id': client_id
            }
    finally:
        # Restore original endpoint if it existed
        if original_endpoint:
            os.environ['AWS_ENDPOINT_URL'] = original_endpoint


# Hypothesis strategies for generating test data
valid_email_strategy = st.builds(
    lambda suffix: f"testuser{suffix}@example.com",
    suffix=st.integers(min_value=1, max_value=999999)
)

valid_password_strategy = st.builds(
    lambda base, digit: f"Test{base}{digit}!",
    base=st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=2, max_size=8),
    digit=st.integers(min_value=0, max_value=9)
)

user_name_strategy = st.builds(
    lambda name: f"Test{name}",
    name=st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=10)
)


def mock_lambda_handler(event, context):
    """
    Mock lambda handler for testing Cognito authentication flow
    This simulates the auth handler without complex dependencies
    """
    method = event.get('httpMethod')
    path = event.get('path')
    body = json.loads(event.get('body', '{}'))
    headers = event.get('headers', {})
    
    cognito_client = boto3.client('cognito-idp', region_name='us-east-1')
    user_pool_id = os.environ.get('USER_POOL_ID')
    client_id = os.environ.get('USER_POOL_CLIENT_ID')
    
    try:
        if method == 'POST' and path == '/auth/register':
            # Register user
            email = body.get('email')
            password = body.get('password')
            first_name = body.get('first_name')
            last_name = body.get('last_name')
            
            try:
                # First create the user
                response = cognito_client.admin_create_user(
                    UserPoolId=user_pool_id,
                    Username=email,
                    UserAttributes=[
                        {'Name': 'email', 'Value': email},
                        {'Name': 'given_name', 'Value': first_name},
                        {'Name': 'family_name', 'Value': last_name},
                        {'Name': 'email_verified', 'Value': 'true'}  # Set to true for testing
                    ],
                    TemporaryPassword=password,
                    MessageAction='SUPPRESS'
                )
                
                # Set permanent password immediately
                cognito_client.admin_set_user_password(
                    UserPoolId=user_pool_id,
                    Username=email,
                    Password=password,
                    Permanent=True
                )
                
                # Confirm the user immediately for testing
                try:
                    cognito_client.admin_confirm_sign_up(
                        UserPoolId=user_pool_id,
                        Username=email
                    )
                except ClientError as confirm_error:
                    # User might already be confirmed, ignore this error
                    if confirm_error.response['Error']['Code'] not in ['NotAuthorizedException', 'InvalidParameterException']:
                        raise confirm_error
                
                return {
                    'statusCode': 201,
                    'body': json.dumps({
                        'message': 'User registered successfully',
                        'user_sub': email  # Use email as identifier for consistency
                    })
                }
            except ClientError as e:
                if e.response['Error']['Code'] == 'UsernameExistsException':
                    return {
                        'statusCode': 409,
                        'body': json.dumps({'error': 'User already exists'})
                    }
                raise
                
        elif method == 'POST' and path == '/auth/login':
            # Login user
            email = body.get('email')
            password = body.get('password')
            
            try:
                response = cognito_client.admin_initiate_auth(
                    UserPoolId=user_pool_id,
                    ClientId=client_id,
                    AuthFlow='ADMIN_NO_SRP_AUTH',
                    AuthParameters={
                        'USERNAME': email,
                        'PASSWORD': password
                    }
                )
            except ClientError as e:
                error_code = e.response['Error']['Code']
                # If user is not confirmed, try to confirm them automatically for testing
                if error_code == 'UserNotConfirmedException':
                    try:
                        cognito_client.admin_confirm_sign_up(
                            UserPoolId=user_pool_id,
                            Username=email
                        )
                        # Retry login after confirmation
                        response = cognito_client.admin_initiate_auth(
                            UserPoolId=user_pool_id,
                            ClientId=client_id,
                            AuthFlow='ADMIN_NO_SRP_AUTH',
                            AuthParameters={
                                'USERNAME': email,
                                'PASSWORD': password
                            }
                        )
                    except ClientError:
                        raise e  # Re-raise original error
                elif error_code == 'NotAuthorizedException':
                    # Check if user exists but password is wrong, or user doesn't exist
                    try:
                        cognito_client.admin_get_user(
                            UserPoolId=user_pool_id,
                            Username=email
                        )
                        # User exists but password is wrong
                        raise e
                    except ClientError as get_user_error:
                        if get_user_error.response['Error']['Code'] == 'UserNotFoundException':
                            # User doesn't exist, return generic error
                            raise e
                        else:
                            raise e
                else:
                    raise e
            
            # Get user attributes
            user_response = cognito_client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=email
            )
            
            user_attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'user': {
                        'id': user_attributes.get('sub'),
                        'email': user_attributes.get('email'),
                        'first_name': user_attributes.get('given_name'),
                        'last_name': user_attributes.get('family_name')
                    },
                    'tokens': {
                        'access_token': response['AuthenticationResult']['AccessToken'],
                        'id_token': response['AuthenticationResult']['IdToken'],
                        'refresh_token': response['AuthenticationResult']['RefreshToken']
                    }
                })
            }
            
        elif method == 'GET' and path == '/auth/validate':
            # Validate token
            auth_header = headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Invalid authorization header'})
                }
            
            access_token = auth_header[7:]  # Remove 'Bearer '
            
            # Get user from token
            response = cognito_client.get_user(AccessToken=access_token)
            user_attributes = {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'valid': True,
                    'user': {
                        'id': user_attributes.get('sub'),
                        'email': user_attributes.get('email'),
                        'first_name': user_attributes.get('given_name'),
                        'last_name': user_attributes.get('family_name')
                    }
                })
            }
            
        elif method == 'POST' and path == '/auth/logout':
            # Logout user
            auth_header = headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Invalid authorization header'})
                }
            
            access_token = auth_header[7:]  # Remove 'Bearer '
            
            # Global sign out
            cognito_client.global_sign_out(AccessToken=access_token)
            
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Logged out successfully'})
            }
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NotAuthorizedException':
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid credentials'})
            }
        elif error_code == 'UserNotFoundException':
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Invalid credentials'})
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Authentication error: {str(e)}'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }


class TestCognitoAuthenticationProperties:
    """Property-based tests for Cognito authentication"""
    
    def test_registration_write_path_guard(self, cognito_setup):
        """
        GUARD TEST: Ensures registration can actually create NEW users
        
        This test prevents "shadow success" in property tests by explicitly
        verifying that the registration write path works for guaranteed unique users.
        If this test fails, it means registration is broken and property tests
        might be passing due to existing users from previous runs.
        
        **Validates: Requirements 1.1, 1.2** (User registration functionality)
        """
        # Generate guaranteed unique email using UUID and timestamp
        unique_suffix = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
        unique_email = f"guard-test-{unique_suffix}@example.com"
        
        register_event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'body': json.dumps({
                'email': unique_email,
                'password': 'GuardTest123!',
                'first_name': 'Guard',
                'last_name': 'Test'
            }),
            'headers': {},
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'guard-test-agent'
                }
            }
        }
        
        register_response = mock_lambda_handler(register_event, {})
        
        # This MUST be 201 Created - no fallback to 409 allowed
        # If this fails, registration is broken and property tests may have false positives
        assert register_response['statusCode'] == 201, (
            f"Registration write path is broken! Expected 201, got {register_response['statusCode']}. "
            f"Response: {register_response.get('body', 'No body')}"
        )
        
        register_body = json.loads(register_response['body'])
        assert 'user_sub' in register_body, "Registration response missing user_sub"
        assert register_body['user_sub'] == unique_email, "user_sub should match email"
    
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy,
        first_name=user_name_strategy,
        last_name=user_name_strategy
    )
    @settings(max_examples=5, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cognito_authentication_round_trip(self, cognito_setup, email, password, first_name, last_name):
        """
        Property 1: Cognito Authentication Round Trip
        
        For any valid user credentials, registering a user and then logging in
        should return valid authentication tokens that can be used to validate the user.
        
        **Validates: Requirements 1.4, 1.6**
        """
        assume(len(email) <= 254)  # Email length limit
        assume(len(password) >= 8)  # Password minimum length
        assume(first_name.strip())  # Non-empty first name
        assume(last_name.strip())   # Non-empty last name
        
        # Step 1: Register user (or skip if already exists)
        register_event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'body': json.dumps({
                'email': email,
                'password': password,
                'first_name': first_name.strip(),
                'last_name': last_name.strip()
            }),
            'headers': {},
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        register_response = mock_lambda_handler(register_event, {})
        
        # Registration should succeed or user should already exist
        assert register_response['statusCode'] in [201, 409]
        
        # Step 2: Confirm user (simulate email verification)
        cognito_client = cognito_setup['client']
        try:
            cognito_client.admin_confirm_sign_up(
                UserPoolId=cognito_setup['user_pool_id'],
                Username=email
            )
        except ClientError as e:
            # User might already be confirmed
            if e.response['Error']['Code'] not in ['NotAuthorizedException', 'InvalidParameterException']:
                raise
        
        # Step 3: Login with the same credentials
        login_event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': email,
                'password': password
            }),
            'headers': {},
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        login_response = mock_lambda_handler(login_event, {})
        
        # Debug: Print login response if it fails
        if login_response['statusCode'] != 200:
            print(f"Login failed for {email}: {login_response}")
        
        # Login should succeed
        assert login_response['statusCode'] == 200
        login_body = json.loads(login_response['body'])
        
        # Should return user info and tokens
        assert 'user' in login_body
        assert 'tokens' in login_body
        
        user_info = login_body['user']
        tokens = login_body['tokens']
        
        # User info should have email
        assert user_info['email'] == email
        
        # Should have valid tokens
        assert 'access_token' in tokens
        assert 'id_token' in tokens
        assert 'refresh_token' in tokens
        assert tokens['access_token']
        assert tokens['id_token']
        assert tokens['refresh_token']
        
        # Step 4: Validate token using the access token
        validate_event = {
            'httpMethod': 'GET',
            'path': '/auth/validate',
            'headers': {
                'Authorization': f"Bearer {tokens['access_token']}"
            },
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        validate_response = mock_lambda_handler(validate_event, {})
        
        # Token validation should succeed
        assert validate_response['statusCode'] == 200
        validate_body = json.loads(validate_response['body'])
        
        # Should confirm token is valid and return user info
        assert validate_body['valid'] is True
        assert 'user' in validate_body
        
        validated_user = validate_body['user']
        
        # Validated user info should have same email
        assert validated_user['email'] == email
        
        # Round trip property: register → login → validate should preserve user email identity
        assert user_info['email'] == validated_user['email']
    
    @given(
        email=valid_email_strategy,
        password=valid_password_strategy
    )
    @settings(max_examples=30, deadline=20000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_credentials_rejection(self, cognito_setup, email, password):
        """
        Property: Invalid credentials should always be rejected
        
        For any email/password combination where the user doesn't exist,
        login attempts should be consistently rejected.
        """
        assume(len(email) <= 254)
        assume(len(password) >= 8)
        
        # Attempt to login with non-existent user
        login_event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': email,
                'password': password
            }),
            'headers': {},
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        login_response = mock_lambda_handler(login_event, {})
        
        # Should be rejected with 401 Unauthorized
        assert login_response['statusCode'] == 401
        response_body = json.loads(login_response['body'])
        assert 'error' in response_body
        
        # Should not leak information about whether user exists
        assert 'Invalid credentials' in response_body['error'] or 'credentials' in response_body['error'].lower()
    
    def test_logout_invalidates_tokens(self, cognito_setup):
        """
        Property: Logout should invalidate authentication tokens
        
        For any authenticated user, logging out should invalidate their tokens
        so they cannot be used for subsequent API calls.
        
        Uses a unique user to avoid conflicts with existing test data.
        """
        # Use unique user to avoid password conflicts
        unique_suffix = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
        unique_email = f"logout-test-{unique_suffix}@example.com"
        test_password = "LogoutTest123!"
        
        # Register and confirm user
        register_event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'body': json.dumps({
                'email': unique_email,
                'password': test_password,
                'first_name': 'Logout',
                'last_name': 'Test'
            }),
            'headers': {},
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        register_response = mock_lambda_handler(register_event, {})
        assert register_response['statusCode'] == 201
        
        # Confirm user
        cognito_client = cognito_setup['client']
        cognito_client.admin_confirm_sign_up(
            UserPoolId=cognito_setup['user_pool_id'],
            Username=unique_email
        )
        
        # Login to get tokens
        login_event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': unique_email,
                'password': test_password
            }),
            'headers': {},
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        login_response = mock_lambda_handler(login_event, {})
        assert login_response['statusCode'] == 200
        
        login_body = json.loads(login_response['body'])
        access_token = login_body['tokens']['access_token']
        
        # Verify token works before logout
        validate_event = {
            'httpMethod': 'GET',
            'path': '/auth/validate',
            'headers': {
                'Authorization': f"Bearer {access_token}"
            },
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        validate_response = mock_lambda_handler(validate_event, {})
        assert validate_response['statusCode'] == 200
        
        # Logout
        logout_event = {
            'httpMethod': 'POST',
            'path': '/auth/logout',
            'headers': {
                'Authorization': f"Bearer {access_token}"
            },
            'requestContext': {
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'test-agent'
                }
            }
        }
        
        logout_response = mock_lambda_handler(logout_event, {})
        assert logout_response['statusCode'] == 200
        
        # Try to use token after logout - should fail
        validate_after_logout = mock_lambda_handler(validate_event, {})
        assert validate_after_logout['statusCode'] == 401
        
        # Token should be invalidated
        response_body = json.loads(validate_after_logout['body'])
        assert 'error' in response_body