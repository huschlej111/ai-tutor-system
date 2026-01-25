"""
Property-based tests for quiz engine service
Feature: tutor-system
"""
import pytest
import json
import uuid
import time
from unittest.mock import patch
from hypothesis import given, strategies as st, settings, HealthCheck
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.quiz_engine.handler import lambda_handler
from lambda_functions.domain_management.handler import lambda_handler as domain_handler
from shared.database import get_db_connection
import psycopg2


def create_cognito_event(user_id, email, method, path, body_data):
    """Create a mock API Gateway event with Cognito authorization context"""
    return {
        'httpMethod': method,
        'path': path,
        'body': json.dumps(body_data),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': email
                }
            }
        }
    }


# Test data generators
@st.composite
def valid_domain_name(draw):
    """Generate valid domain names"""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'), min_codepoint=32, max_codepoint=126),
        min_size=2, max_size=100
    ).filter(lambda x: x.strip() and len(x.strip()) >= 2))


@st.composite
def valid_domain_description(draw):
    """Generate valid domain descriptions"""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Ps', 'Pe'), min_codepoint=32, max_codepoint=126),
        min_size=10, max_size=500
    ).filter(lambda x: x.strip() and len(x.strip()) >= 10))


@st.composite
def valid_term(draw):
    """Generate valid terms"""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd'), min_codepoint=32, max_codepoint=126),
        min_size=2, max_size=200
    ).filter(lambda x: x.strip() and len(x.strip()) >= 2))


@st.composite
def valid_definition(draw):
    """Generate valid definitions"""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Ps', 'Pe'), min_codepoint=32, max_codepoint=126),
        min_size=10, max_size=1000
    ).filter(lambda x: x.strip() and len(x.strip()) >= 10))


@st.composite
def quiz_domain_with_terms(draw):
    """Generate a domain with terms suitable for quiz testing"""
    # Generate simpler, smaller domain name
    domain_name = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        min_size=3, max_size=20
    ))
    
    # Add timestamp to ensure uniqueness
    unique_suffix = str(int(time.time() * 1000000))[-6:]
    domain_name = f"{domain_name}_{unique_suffix}"
    
    domain_description = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?',
        min_size=12, max_size=50
    ).filter(lambda x: len(x.strip()) >= 10))
    
    # Generate 2-3 terms for the quiz (smaller for faster testing)
    num_terms = draw(st.integers(min_value=2, max_value=3))
    terms = []
    
    for i in range(num_terms):
        term = f"Term{i}_{unique_suffix}"  # Simple unique term names
        definition = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?',
            min_size=12, max_size=50
        ).filter(lambda x: len(x.strip()) >= 10))
        terms.append({
            'term': term,
            'definition': definition
        })
    
    return {
        'name': domain_name,
        'description': domain_description,
        'terms': terms
    }


def create_test_user():
    """Create a test user directly in the database and return user info"""
    unique_id = str(uuid.uuid4())[:8]
    user_id = str(uuid.uuid4())
    email = f'test_{unique_id}@example.com'
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Insert test user directly into database with a dummy password hash
                cursor.execute("""
                    INSERT INTO users (id, email, password_hash, first_name, last_name, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (user_id, email, 'dummy_hash_for_testing', 'Test', 'User'))
                
                result = cursor.fetchone()
                if result:
                    user_id = result[0]
                
                cursor.close()
                conn.commit()
                
                return user_id, email
                
        except Exception as e:
            if "Secret not found" in str(e) and attempt < max_retries - 1:
                print(f"Attempt {attempt + 1}: Secrets Manager not ready, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                raise Exception(f"Failed to create test user after {max_retries} attempts: {e}")


def cleanup_test_user(email: str):
    """Clean up test user and associated data"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Delete user (cascade will handle domains and terms)
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            conn.commit()
            cursor.close()
    except Exception:
        pass  # Ignore cleanup errors


def create_domain_with_terms(user_id: str, email: str, domain_data: dict) -> str:
    """Helper function to create a domain with terms and return domain_id"""
    # Create domain
    create_domain_event = {
        'httpMethod': 'POST',
        'path': '/domains',
        'body': json.dumps({
            'name': domain_data['name'],
            'description': domain_data['description']
        }),
        'headers': {},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': email,
                    'cognito:username': email,
                    'email_verified': 'true'
                }
            }
        }
    }
    
    create_response = domain_handler(create_domain_event, {})
    assert create_response['statusCode'] == 201
    
    domain_id = json.loads(create_response['body'])['data']['id']
    
    # Add terms to domain
    add_terms_event = {
        'httpMethod': 'POST',
        'path': f'/domains/{domain_id}/terms',
        'pathParameters': {
            'domain_id': domain_id
        },
        'body': json.dumps({'terms': domain_data['terms']}),
        'headers': {},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': email,
                    'cognito:username': email,
                    'email_verified': 'true'
                }
            }
        }
    }
    
    add_terms_response = domain_handler(add_terms_event, {})
    assert add_terms_response['statusCode'] == 201
    
    return domain_id


@given(domain_data=quiz_domain_with_terms())
@settings(max_examples=100, deadline=60000, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.large_base_example])  # 60 second timeout per test
@pytest.mark.localstack
def test_quiz_session_state_preservation(domain_data, test_environment, clean_database):
    """
    Property 3: Quiz Session State Preservation
    For any quiz session that is paused and resumed, the student should continue from 
    the exact same question and progress state as when they paused.
    **Validates: Requirements 3.5, 3.6**
    """
    user_id, email = create_test_user()
    
    # Create mock event with Cognito context
    def create_quiz_event(method, path, body_data):
        return {
            'httpMethod': method,
            'path': path,
            'body': json.dumps(body_data),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email
                    }
                }
            }
        }
    
    try:
        # Step 1: Create domain with terms
        domain_id = create_domain_with_terms(user_id, email, domain_data)
        
        # Step 2: Start quiz session
        start_quiz_event = create_quiz_event('POST', '/quiz/start', {
            'domain_id': domain_id
        })
        
        start_response = lambda_handler(start_quiz_event, {})
        
        # Verify quiz started successfully
        assert start_response['statusCode'] == 200
        start_body = json.loads(start_response['body'])
        
        session_id = start_body['session_id']
        original_question = start_body['current_question']
        original_progress = start_body['progress']
        
        # Verify initial state
        assert original_question is not None
        assert original_progress['current_index'] == 0
        assert original_progress['total_questions'] == len(domain_data['terms'])
        assert original_progress['completed'] is False
        
        # Step 3: Pause the quiz session
        pause_quiz_event = create_quiz_event('POST', '/quiz/pause', {
            'session_id': session_id
        })
        
        pause_response = lambda_handler(pause_quiz_event, {})
        
        # Verify quiz paused successfully
        assert pause_response['statusCode'] == 200
        pause_body = json.loads(pause_response['body'])
        assert pause_body['status'] == 'paused'
        
        # Step 4: Resume the quiz session
        resume_quiz_event = create_quiz_event('POST', '/quiz/resume', {
            'session_id': session_id
        })
        
        resume_response = lambda_handler(resume_quiz_event, {})
        
        # Verify quiz resumed successfully
        assert resume_response['statusCode'] == 200
        resume_body = json.loads(resume_response['body'])
        
        resumed_question = resume_body['current_question']
        resumed_progress = resume_body['progress']
        
        # Property verification: Quiz Session State Preservation
        # The resumed session should have exactly the same state as when paused
        
        # Verify question state is preserved
        assert resumed_question is not None
        assert resumed_question['term_id'] == original_question['term_id']
        assert resumed_question['term'] == original_question['term']
        assert resumed_question['question_number'] == original_question['question_number']
        assert resumed_question['total_questions'] == original_question['total_questions']
        
        # Verify progress state is preserved
        assert resumed_progress['current_index'] == original_progress['current_index']
        assert resumed_progress['total_questions'] == original_progress['total_questions']
        assert resumed_progress['completed'] == original_progress['completed']
        
        # Verify session metadata is preserved
        assert resume_body['session_id'] == session_id
        assert resume_body['domain_name'] == start_body['domain_name']
        
    finally:
        # Cleanup: Remove test user and associated data
        cleanup_test_user(email)


@pytest.mark.localstack
def test_quiz_session_state_preservation_edge_cases(test_environment, clean_database):
    """
    Test quiz session state preservation edge cases
    """
    user_id, email = create_test_user()
    
    # Create mock event with Cognito context
    def create_quiz_event(method, path, body_data):
        return {
            'httpMethod': method,
            'path': path,
            'body': json.dumps(body_data),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email
                    }
                }
            }
        }
    
    try:
        # Create a simple domain for testing
        domain_data = {
            'name': 'Test Domain',
            'description': 'Test domain for edge case testing',
            'terms': [
                {'term': 'Term1', 'definition': 'Definition for term 1'},
                {'term': 'Term2', 'definition': 'Definition for term 2'},
                {'term': 'Term3', 'definition': 'Definition for term 3'}
            ]
        }
        
        domain_id = create_domain_with_terms(user_id, email, domain_data)
        
        # Test 1: Cannot pause non-existent session
        pause_invalid_event = create_quiz_event('POST', '/quiz/pause', {
            'session_id': str(uuid.uuid4())  # Non-existent session
        })
        
        pause_invalid_response = lambda_handler(pause_invalid_event, {})
        assert pause_invalid_response['statusCode'] == 404
        
        # Test 2: Cannot resume non-existent session
        resume_invalid_event = create_quiz_event('POST', '/quiz/resume', {
            'session_id': str(uuid.uuid4())  # Non-existent session
        })
        
        resume_invalid_response = lambda_handler(resume_invalid_event, {})
        assert resume_invalid_response['statusCode'] == 404
        
        # Test 3: Start quiz and test multiple pause/resume cycles
        start_quiz_event = create_quiz_event('POST', '/quiz/start', {
            'domain_id': domain_id
        })
        
        start_response = lambda_handler(start_quiz_event, {})
        assert start_response['statusCode'] == 200
        
        session_id = json.loads(start_response['body'])['session_id']
        
        # Multiple pause/resume cycles
        for cycle in range(3):
            # Pause
            pause_event = create_quiz_event('POST', '/quiz/pause', {
                'session_id': session_id
            })
            
            pause_response = lambda_handler(pause_event, {})
            assert pause_response['statusCode'] == 200
            
            # Resume
            resume_event = create_quiz_event('POST', '/quiz/resume', {
                'session_id': session_id
            })
            
            resume_response = lambda_handler(resume_event, {})
            assert resume_response['statusCode'] == 200
            
            # Verify state is consistent after each cycle
            resume_body = json.loads(resume_response['body'])
            assert resume_body['status'] == 'resumed'
            assert resume_body['session_id'] == session_id
        
        # Test 4: Cannot pause already paused session
        pause_response = lambda_handler(pause_event, {})
        assert pause_response['statusCode'] == 200
        
        # Try to pause again
        pause_again_response = lambda_handler(pause_event, {})
        assert pause_again_response['statusCode'] == 400  # Cannot pause already paused session
        
        # Test 5: Cannot resume active session
        resume_response = lambda_handler(resume_event, {})
        assert resume_response['statusCode'] == 200
        
        # Try to resume again
        resume_again_response = lambda_handler(resume_event, {})
        assert resume_again_response['statusCode'] == 400  # Cannot resume active session
        
    finally:
        cleanup_test_user(email)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])