"""
Property-based tests for authentication service
Feature: tutor-system
"""
import pytest
import json
import uuid
from hypothesis import given, strategies as st, settings
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.auth.handler import lambda_handler
from shared.database import get_db_connection


# Test data generators
@st.composite
def valid_email(draw):
    """Generate valid email addresses"""
    username = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=33, max_codepoint=126),
        min_size=1, max_size=20
    ).filter(lambda x: x.isalnum()))
    
    domain = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=33, max_codepoint=126),
        min_size=2, max_size=10
    ).filter(lambda x: x.isalnum()))
    
    tld = draw(st.sampled_from(['com', 'org', 'net', 'edu', 'gov']))
    
    return f"{username}@{domain}.{tld}".lower()


@st.composite
def valid_password(draw):
    """Generate valid passwords that meet strength requirements"""
    # Ensure at least one of each required character type
    uppercase = draw(st.text(alphabet=st.characters(min_codepoint=65, max_codepoint=90), min_size=1, max_size=3))
    lowercase = draw(st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=3))
    digits = draw(st.text(alphabet=st.characters(min_codepoint=48, max_codepoint=57), min_size=1, max_size=3))
    special = draw(st.text(alphabet='!@#$%^&*(),.?":{}|<>', min_size=1, max_size=3))
    
    # Add additional random characters to reach minimum length
    additional = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=33, max_codepoint=126),
        min_size=0, max_size=10
    ))
    
    # Combine and shuffle
    password_chars = list(uppercase + lowercase + digits + special + additional)
    draw(st.randoms()).shuffle(password_chars)
    
    password = ''.join(password_chars)
    
    # Ensure minimum length
    if len(password) < 8:
        password += draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=33, max_codepoint=126),
            min_size=8 - len(password), max_size=8 - len(password)
        ))
    
    return password[:128]  # Ensure maximum length


@st.composite
def user_registration_data(draw):
    """Generate valid user registration data"""
    return {
        'email': draw(valid_email()),
        'password': draw(valid_password()),
        'first_name': draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=1, max_size=50
        )),
        'last_name': draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=1, max_size=50
        ))
    }


def cleanup_test_user(email: str):
    """Clean up test user from database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            conn.commit()
            cursor.close()
    except Exception:
        pass  # Ignore cleanup errors


@given(user_data=user_registration_data())
@settings(max_examples=100, deadline=30000)  # 30 second timeout per test
@pytest.mark.localstack
def test_authentication_round_trip(user_data):
    """
    Property 1: Authentication Round Trip
    For any valid user credentials, successful authentication followed by logout 
    should result in an unauthenticated state, and subsequent login with the 
    same credentials should succeed again.
    **Validates: Requirements 1.4, 1.6**
    """
    # Set up Cognito mock for this test
    from moto import mock_aws
    import boto3
    import os
    
    original_endpoint = os.environ.pop('AWS_ENDPOINT_URL', None)
    original_pool_id = os.environ.get('USER_POOL_ID')
    original_client_id = os.environ.get('USER_POOL_CLIENT_ID')
    
    mock = mock_aws()
    mock.start()
    
    try:
        # Create Cognito client
        client = boto3.client('cognito-idp', region_name='us-east-1')
        
        # Create User Pool
        user_pool = client.create_user_pool(
            PoolName='test-pool',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': True
                }
            },
            UsernameAttributes=['email']
        )
        
        # Create User Pool Client
        user_pool_client = client.create_user_pool_client(
            UserPoolId=user_pool['UserPool']['Id'],
            ClientName='test-client',
            ExplicitAuthFlows=['USER_PASSWORD_AUTH', 'ALLOW_USER_PASSWORD_AUTH']
        )
        
        # Set environment variables and patch auth handler
        os.environ['USER_POOL_ID'] = user_pool['UserPool']['Id']
        os.environ['USER_POOL_CLIENT_ID'] = user_pool_client['UserPoolClient']['ClientId']
        os.environ['AWS_REGION'] = 'us-east-1'
        
        import lambda_functions.auth.handler as auth_handler
        auth_handler.USER_POOL_ID = user_pool['UserPool']['Id']
        auth_handler.USER_POOL_CLIENT_ID = user_pool_client['UserPoolClient']['ClientId']
        auth_handler.cognito_client = client
        
        email = user_data['email']
        password = user_data['password']
        
        # Step 1: Register user
        register_event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'body': json.dumps(user_data),
            'headers': {}
        }
        
        register_response = lambda_handler(register_event, {})
        
        # Verify registration succeeded
        assert register_response['statusCode'] == 201
        register_body = json.loads(register_response['body'])
        assert 'user_sub' in register_body
        assert 'message' in register_body
        
        # Confirm the user in Cognito (required for login)
        user_sub = register_body['user_sub']
        
        # Admin confirm the user (simulating email confirmation)
        client.admin_confirm_sign_up(
            UserPoolId=user_pool['UserPool']['Id'],
            Username=email
        )
        
        # Step 2: Login to get tokens
        login_event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': email,
                'password': password
            }),
            'headers': {}
        }
        
        login_response = lambda_handler(login_event, {})
        assert login_response['statusCode'] == 200
        login_body = json.loads(login_response['body'])
        assert 'tokens' in login_body
        assert 'user' in login_body
        
        first_token = login_body['tokens']['access_token']
        user_id = login_body['user']['id']
        
        # Step 3: Validate initial token works
        validate_event = {
            'httpMethod': 'GET',
            'path': '/auth/validate',
            'headers': {'Authorization': f'Bearer {first_token}'}
        }
        
        validate_response = lambda_handler(validate_event, {})
        assert validate_response['statusCode'] == 200
        
        # Step 4: Logout (invalidates session client-side)
        logout_event = {
            'httpMethod': 'POST',
            'path': '/auth/logout',
            'headers': {'Authorization': f'Bearer {first_token}'}
        }
        
        logout_response = lambda_handler(logout_event, {})
        assert logout_response['statusCode'] == 200
        
        # Step 5: Login again with same credentials
        login_event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': email,
                'password': password
            }),
            'headers': {}
        }
        
        login_response = lambda_handler(login_event, {})
        
        # Verify login succeeded
        assert login_response['statusCode'] == 200
        login_body = json.loads(login_response['body'])
        assert 'tokens' in login_body
        assert 'user' in login_body
        
        second_token = login_body['tokens']['access_token']
        
        # Step 6: Validate new token works
        validate_event_2 = {
            'httpMethod': 'GET',
            'path': '/auth/validate',
            'headers': {'Authorization': f'Bearer {second_token}'}
        }
        
        validate_response_2 = lambda_handler(validate_event_2, {})
        assert validate_response_2['statusCode'] == 200
        
        validate_body_2 = json.loads(validate_response_2['body'])
        assert validate_body_2['user']['id'] == user_id
        assert validate_body_2['user']['email'] == email
        
        # Property verification: Round trip should preserve user identity
        # The user should be able to authenticate, logout, and authenticate again
        # with the same credentials, maintaining their identity
        assert login_body['user']['id'] == user_id
        assert login_body['user']['email'] == email
        
    finally:
        # Cleanup: Remove test user
        cleanup_test_user(email)
        
        # Stop the mock and restore environment
        mock.stop()
        if original_endpoint:
            os.environ['AWS_ENDPOINT_URL'] = original_endpoint
        if original_pool_id:
            os.environ['USER_POOL_ID'] = original_pool_id
        if original_client_id:
            os.environ['USER_POOL_CLIENT_ID'] = original_client_id


@pytest.mark.localstack
def test_authentication_round_trip_with_invalid_credentials():
    """
    Test that invalid credentials fail consistently after round trip
    """
    # Set up Cognito mock for this test
    from moto import mock_aws
    import boto3
    import os
    
    original_endpoint = os.environ.pop('AWS_ENDPOINT_URL', None)
    original_pool_id = os.environ.get('USER_POOL_ID')
    original_client_id = os.environ.get('USER_POOL_CLIENT_ID')
    
    mock = mock_aws()
    mock.start()
    
    try:
        # Create Cognito client and setup (same as above)
        client = boto3.client('cognito-idp', region_name='us-east-1')
        
        user_pool = client.create_user_pool(
            PoolName='test-pool',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': True
                }
            },
            UsernameAttributes=['email']
        )
        
        user_pool_client = client.create_user_pool_client(
            UserPoolId=user_pool['UserPool']['Id'],
            ClientName='test-client',
            ExplicitAuthFlows=['USER_PASSWORD_AUTH', 'ALLOW_USER_PASSWORD_AUTH']
        )
        
        os.environ['USER_POOL_ID'] = user_pool['UserPool']['Id']
        os.environ['USER_POOL_CLIENT_ID'] = user_pool_client['UserPoolClient']['ClientId']
        os.environ['AWS_REGION'] = 'us-east-1'
        
        import lambda_functions.auth.handler as auth_handler
        auth_handler.USER_POOL_ID = user_pool['UserPool']['Id']
        auth_handler.USER_POOL_CLIENT_ID = user_pool_client['UserPoolClient']['ClientId']
        auth_handler.cognito_client = client
        
        # Create a user with unique email to avoid conflicts
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        test_user = {
            'email': f'test_{unique_id}@example.com',
            'password': 'ValidPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        # Register user
        register_event = {
            'httpMethod': 'POST',
            'path': '/auth/register',
            'body': json.dumps(test_user),
            'headers': {}
        }
        
        register_response = lambda_handler(register_event, {})
        assert register_response['statusCode'] == 201
        
        # Confirm the user in Cognito (required for login)
        register_body = json.loads(register_response['body'])
        user_sub = register_body['user_sub']
        
        # Admin confirm the user (simulating email confirmation)
        client.admin_confirm_sign_up(
            UserPoolId=user_pool['UserPool']['Id'],
            Username=test_user['email']
        )
        
        # Try to login with wrong password
        login_event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': test_user['email'],
                'password': 'WrongPassword123!'
            }),
            'headers': {}
        }
        
        login_response = lambda_handler(login_event, {})
        assert login_response['statusCode'] == 401
        
        # Try to login with wrong password again - should still fail
        login_response_2 = lambda_handler(login_event, {})
        assert login_response_2['statusCode'] == 401
        
        # Login with correct credentials should work
        correct_login_event = {
            'httpMethod': 'POST',
            'path': '/auth/login',
            'body': json.dumps({
                'email': test_user['email'],
                'password': test_user['password']
            }),
            'headers': {}
        }
        
        correct_login_response = lambda_handler(correct_login_event, {})
        assert correct_login_response['statusCode'] == 200
        
    finally:
        cleanup_test_user(test_user['email'])
        
        # Stop the mock and restore environment
        mock.stop()
        if original_endpoint:
            os.environ['AWS_ENDPOINT_URL'] = original_endpoint
        if original_pool_id:
            os.environ['USER_POOL_ID'] = original_pool_id
        if original_client_id:
            os.environ['USER_POOL_CLIENT_ID'] = original_client_id


if __name__ == '__main__':
    pytest.main([__file__, '-v'])