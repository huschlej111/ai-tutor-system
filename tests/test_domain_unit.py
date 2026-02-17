"""
Unit tests for domain management service
Requirements: 2.3, 2.4
"""
import pytest
import json
import uuid
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.domain_management.handler import lambda_handler
from lambda_functions.auth.handler import lambda_handler as auth_handler
from shared.database import get_db_connection


def create_test_user():
    """Create a test user and return authentication token"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        'email': f'test_{unique_id}@example.com',
        'password': 'TestPass123!',
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    register_event = {
        'httpMethod': 'POST',
        'path': '/auth/register',
        'body': json.dumps(user_data),
        'headers': {},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'cognito:groups': 'student'  # Add required group for authorization
                }
            }
        }
    }
    
    response = auth_handler(register_event, {})
    if response['statusCode'] not in [201, 200]:
        # If registration fails, try to create user directly in database for testing
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                user_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO users (id, email, password_hash, first_name, last_name, is_active, is_verified) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (user_id, user_data['email'], 'test_hash', user_data['first_name'], user_data['last_name'], True, True)
                )
                conn.commit()
                cursor.close()
                
                # Return a mock token for testing
                return f"test_token_{unique_id}", user_id, user_data['email']
        except Exception as e:
            raise Exception(f"Failed to create test user: {e}")
    
    body = json.loads(response['body'])
    return body.get('token', f"test_token_{unique_id}"), body.get('user', {}).get('id', str(uuid.uuid4())), user_data['email']


def create_domain_event(method, path, body_data, token, user_id, email):
    """Create a domain management event with proper Cognito authorization"""
    return {
        'httpMethod': method,
        'path': path,
        'body': json.dumps(body_data),
        'headers': {'Authorization': f'Bearer {token}'},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': email,
                    'cognito:username': email,
                    'cognito:groups': 'student',  # Students can manage their own domains
                    'email_verified': 'true',
                    'token_use': 'access'
                }
            }
        },
        'pathParameters': {'domain_id': path.split('/')[-1]} if '{' in path else None
    }


def cleanup_test_user(email: str):
    """Clean up test user and associated data"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            conn.commit()
            cursor.close()
    except Exception:
        pass


class TestDomainValidation:
    """Test domain validation requirements"""
    
    def test_domain_name_required(self):
        """Test that domain name is required"""
        token, user_id, email = create_test_user()
        
        try:
            event = create_domain_event(
                'POST', '/domains',
                {'description': 'Valid description for testing'},
                token, user_id, email
            )
            
            response = lambda_handler(event, {})
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'validation_errors' in body['error']['details']
            assert 'name' in body['error']['details']['validation_errors']
            
        finally:
            cleanup_test_user(email)
    
    def test_domain_description_required(self):
        """Test that domain description is required"""
        token, user_id, email = create_test_user()
        
        try:
            event = create_domain_event(
                'POST', '/domains',
                {'name': 'Valid Domain Name'},
                token, user_id, email
            )
            
            response = lambda_handler(event, {})
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'validation_errors' in body['error']['details']
            assert 'description' in body['error']['details']['validation_errors']
            
        finally:
            cleanup_test_user(email)
    
    def test_domain_name_length_validation(self):
        """Test domain name character limits"""
        token, user_id, email = create_test_user()
        
        try:
            # Test name too short
            event = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'A',  # 1 character, minimum is 2
                    'description': 'Valid description for testing'
                },
                token, user_id, email
            )
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'name' in body['error']['details']['validation_errors']
            
            # Test name too long
            event = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'A' * 101,  # 101 characters, maximum is 100
                    'description': 'Valid description for testing'
                },
                token, user_id, email
            )
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'name' in body['error']['details']['validation_errors']
            
        finally:
            cleanup_test_user(email)
    
    def test_domain_description_length_validation(self):
        """Test domain description character limits"""
        token, user_id, email = create_test_user()
        
        try:
            # Test description too short
            event = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'Valid Domain Name',
                    'description': 'Short'  # 5 characters, minimum is 10
                },
                token, user_id, email
            )
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'description' in body['error']['details']['validation_errors']
            
            # Test description too long
            event = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'Valid Domain Name',
                    'description': 'A' * 501  # 501 characters, maximum is 500
                },
                token, user_id, email
            )
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'description' in body['error']['details']['validation_errors']
            
        finally:
            cleanup_test_user(email)
    
    def test_domain_special_characters_handling(self):
        """Test domain handling of special characters"""
        token, user_id, email = create_test_user()
        
        try:
            # Test domain with special characters (should be allowed)
            event = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'AWS-EC2 & S3 (Cloud Services)',
                    'description': 'Domain with special chars: @#$%^&*()_+-=[]{}|;:,.<>?'
                },
                token, user_id, email
            )
            
            response = lambda_handler(event, {})
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['data']['name'] == 'AWS-EC2 & S3 (Cloud Services)'
            
        finally:
            cleanup_test_user(email)
    
    def test_domain_duplicate_prevention(self):
        """Test domain duplicate prevention within user scope"""
        token, user_id, email = create_test_user()
        
        try:
            domain_data = {
                'name': 'Test Domain',
                'description': 'This is a test domain for duplicate testing'
            }
            
            # Create first domain
            event = create_domain_event(
                'POST', '/domains',
                domain_data,
                token, user_id, email
            )
            
            response1 = lambda_handler(event, {})
            assert response1['statusCode'] == 201
            
            # Try to create duplicate domain
            response2 = lambda_handler(event, {})
            assert response2['statusCode'] == 409
            body = json.loads(response2['body'])
            assert 'already exists' in body['error']['message']
            
        finally:
            cleanup_test_user(email)
    
    def test_domain_deletion_cascade(self):
        """Test domain deletion and cascade operations"""
        token, user_id, email = create_test_user()
        
        try:
            # Create domain
            create_event = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'Test Domain for Deletion',
                    'description': 'This domain will be deleted to test cascade'
                },
                token, user_id, email
            )
            
            create_response = lambda_handler(create_event, {})
            assert create_response['statusCode'] == 201
            domain_id = json.loads(create_response['body'])['data']['id']
            
            # Add terms to domain
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {'term': 'Test Term 1', 'definition': 'Definition for test term 1'},
                        {'term': 'Test Term 2', 'definition': 'Definition for test term 2'}
                    ]
                },
                token, user_id, email
            )
            
            add_terms_response = lambda_handler(add_terms_event, {})
            assert add_terms_response['statusCode'] == 201
            
            # Verify terms exist
            get_terms_event = create_domain_event(
                'GET', f'/domains/{domain_id}/terms',
                {},
                token, user_id, email
            )
            
            get_terms_response = lambda_handler(get_terms_event, {})
            assert get_terms_response['statusCode'] == 200
            terms_body = json.loads(get_terms_response['body'])
            assert len(terms_body['data']) == 2
            
            # Delete domain
            delete_event = create_domain_event(
                'DELETE', f'/domains/{domain_id}',
                {},
                token, user_id, email
            )
            
            delete_response = lambda_handler(delete_event, {})
            assert delete_response['statusCode'] == 200
            
            # Verify domain is deleted
            get_domain_event = create_domain_event(
                'GET', f'/domains/{domain_id}',
                {},
                token, user_id, email
            )
            
            get_domain_response = lambda_handler(get_domain_event, {})
            assert get_domain_response['statusCode'] == 404
            
            # Verify terms are also deleted (cascade)
            get_terms_after_delete = lambda_handler(get_terms_event, {})
            assert get_terms_after_delete['statusCode'] == 404
            
        finally:
            cleanup_test_user(email)


class TestTermValidation:
    """Test term validation requirements"""
    
    def test_term_name_required(self):
        """Test that term name is required"""
        token, user_id, email = create_test_user()
        
        try:
            # Create domain first
            create_domain_event_data = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'Test Domain',
                    'description': 'Domain for term validation testing'
                },
                token, user_id, email
            )
            
            create_response = lambda_handler(create_domain_event_data, {})
            assert create_response['statusCode'] == 201
            domain_id = json.loads(create_response['body'])['data']['id']
            
            # Try to add term without name
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {'definition': 'Definition without term name'}
                    ]
                },
                token, user_id, email
            )
            
            response = lambda_handler(add_terms_event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'validation_errors' in body['error']['details']
            assert 'terms[0].term' in body['error']['details']['validation_errors']
            
        finally:
            cleanup_test_user(email)
    
    def test_term_definition_required(self):
        """Test that term definition is required"""
        token, user_id, email = create_test_user()
        
        try:
            # Create domain first
            create_domain_event_data = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'Test Domain',
                    'description': 'Domain for term validation testing'
                },
                token, user_id, email
            )
            
            create_response = lambda_handler(create_domain_event_data, {})
            assert create_response['statusCode'] == 201
            domain_id = json.loads(create_response['body'])['data']['id']
            
            # Try to add term without definition
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {'term': 'Term without definition'}
                    ]
                },
                token, user_id, email
            )
            
            response = lambda_handler(add_terms_event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'validation_errors' in body['error']['details']
            assert 'terms[0].definition' in body['error']['details']['validation_errors']
            
        finally:
            cleanup_test_user(email)
    
    def test_term_length_validation(self):
        """Test term character limits"""
        token, user_id, email = create_test_user()
        
        try:
            # Create domain first
            create_domain_event_data = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'Test Domain',
                    'description': 'Domain for term validation testing'
                },
                token, user_id, email
            )
            
            create_response = lambda_handler(create_domain_event_data, {})
            assert create_response['statusCode'] == 201
            domain_id = json.loads(create_response['body'])['data']['id']
            
            # Test term name too short
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {
                            'term': 'A',  # 1 character, minimum is 2
                            'definition': 'Valid definition for testing'
                        }
                    ]
                },
                token, user_id, email
            )
            
            response = lambda_handler(add_terms_event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'terms[0].term' in body['error']['details']['validation_errors']
            
            # Test term name too long
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {
                            'term': 'A' * 201,  # 201 characters, maximum is 200
                            'definition': 'Valid definition for testing'
                        }
                    ]
                },
                token, user_id, email
            )
            
            response = lambda_handler(add_terms_event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'terms[0].term' in body['error']['details']['validation_errors']
            
            # Test definition too short
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {
                            'term': 'Valid Term',
                            'definition': 'Short'  # 5 characters, minimum is 10
                        }
                    ]
                },
                token, user_id, email
            )
            
            response = lambda_handler(add_terms_event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'terms[0].definition' in body['error']['details']['validation_errors']
            
            # Test definition too long
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {
                            'term': 'Valid Term',
                            'definition': 'A' * 1001  # 1001 characters, maximum is 1000
                        }
                    ]
                },
                token, user_id, email
            )
            
            response = lambda_handler(add_terms_event, {})
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'terms[0].definition' in body['error']['details']['validation_errors']
            
        finally:
            cleanup_test_user(email)
    
    def test_term_duplicate_prevention_within_domain(self):
        """Test term duplicate prevention within the same domain"""
        token, user_id, email = create_test_user()
        
        try:
            # Create domain first
            create_domain_event_data = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'Test Domain',
                    'description': 'Domain for term duplicate testing'
                },
                token, user_id, email
            )
            
            create_response = lambda_handler(create_domain_event_data, {})
            assert create_response['statusCode'] == 201
            domain_id = json.loads(create_response['body'])['data']['id']
            
            # Add first term
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {
                            'term': 'Duplicate Term',
                            'definition': 'First definition of this term'
                        }
                    ]
                },
                token, user_id, email
            )
            
            response1 = lambda_handler(add_terms_event, {})
            assert response1['statusCode'] == 201
            
            # Try to add duplicate term
            add_duplicate_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {
                            'term': 'Duplicate Term',
                            'definition': 'Second definition of this term'
                        }
                    ]
                },
                token, user_id, email
            )
            
            response2 = lambda_handler(add_duplicate_event, {})
            assert response2['statusCode'] == 400
            body = json.loads(response2['body'])
            assert 'already exists' in body['error']['details']['validation_errors']['terms[0].term']
            
        finally:
            cleanup_test_user(email)
    
    def test_term_special_characters_handling(self):
        """Test term handling of special characters"""
        token, user_id, email = create_test_user()
        
        try:
            # Create domain first
            create_domain_event_data = create_domain_event(
                'POST', '/domains',
                {
                    'name': 'Test Domain',
                    'description': 'Domain for special character testing'
                },
                token, user_id, email
            )
            
            create_response = lambda_handler(create_domain_event_data, {})
            assert create_response['statusCode'] == 201
            domain_id = json.loads(create_response['body'])['data']['id']
            
            # Add term with special characters
            add_terms_event = create_domain_event(
                'POST', f'/domains/{domain_id}/terms',
                {
                    'terms': [
                        {
                            'term': 'C++ & Python (Programming)',
                            'definition': 'Programming languages with special chars: @#$%^&*()_+-=[]{}|;:,.<>?'
                        }
                    ]
                },
                token, user_id, email
            )
            
            response = lambda_handler(add_terms_event, {})
            assert response['statusCode'] == 201
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['data']['terms'][0]['term'] == 'C++ & Python (Programming)'
            
        finally:
            cleanup_test_user(email)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])