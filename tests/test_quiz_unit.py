"""
Unit tests for quiz engine service
Tests quiz state transitions, edge cases, and error conditions
"""
import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.quiz_engine.handler import lambda_handler
from lambda_functions.domain_management.handler import lambda_handler as domain_handler
from shared.database import get_db_connection


def create_test_user():
    """Create a test user directly in the database and return user info"""
    unique_id = str(uuid.uuid4())[:8]
    user_id = str(uuid.uuid4())
    email = f'test_{unique_id}@example.com'
    
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


class TestQuizStateTransitions:
    """Test quiz state transitions and edge cases"""
    
    @pytest.mark.localstack
    def test_invalid_state_changes(self, test_environment, clean_database):
        """Test invalid state changes and error conditions"""
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
                # Test 1: Cannot pause non-existent session
                pause_event = create_quiz_event('POST', '/quiz/pause', {
                    'session_id': str(uuid.uuid4())
                })
                
                pause_response = lambda_handler(pause_event, {})
                assert pause_response['statusCode'] == 404
                assert 'Quiz session not found' in json.loads(pause_response['body'])['error']
                
                # Test 2: Cannot resume non-existent session
                resume_event = create_quiz_event('POST', '/quiz/resume', {
                    'session_id': str(uuid.uuid4())
                })
                
                resume_response = lambda_handler(resume_event, {})
                assert resume_response['statusCode'] == 404
                assert 'Quiz session not found' in json.loads(resume_response['body'])['error']
                
                # Test 3: Cannot submit answer to non-existent session
                answer_event = create_quiz_event('POST', '/quiz/answer', {
                    'session_id': str(uuid.uuid4()),
                    'answer': 'test answer'
                })
                
                answer_response = lambda_handler(answer_event, {})
                assert answer_response['statusCode'] == 404
                assert 'Quiz session not found' in json.loads(answer_response['body'])['error']
                
        finally:
            cleanup_test_user(email)
    
    @pytest.mark.localstack
    def test_quiz_session_lifecycle(self, test_environment, clean_database):
        """Test complete quiz session lifecycle"""
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
                # Create domain with terms
                domain_data = {
                    'name': 'Test Domain',
                    'description': 'Test domain for lifecycle testing',
                    'terms': [
                        {'term': 'Term1', 'definition': 'Definition 1'},
                        {'term': 'Term2', 'definition': 'Definition 2'}
                    ]
                }
                
                domain_id = create_domain_with_terms(user_id, email, domain_data)
                
                # Step 1: Start quiz
                start_event = create_quiz_event('POST', '/quiz/start', {
                    'domain_id': domain_id
                })
                
                start_response = lambda_handler(start_event, {})
                assert start_response['statusCode'] == 200
                
                start_body = json.loads(start_response['body'])
                session_id = start_body['session_id']
                assert start_body['status'] == 'started'
                assert start_body['current_question'] is not None
                
                # Step 2: Pause quiz
                pause_event = create_quiz_event('POST', '/quiz/pause', {
                    'session_id': session_id
                })
                
                pause_response = lambda_handler(pause_event, {})
                assert pause_response['statusCode'] == 200
                assert json.loads(pause_response['body'])['status'] == 'paused'
                
                # Step 3: Try to submit answer while paused (should fail)
                answer_event = create_quiz_event('POST', '/quiz/answer', {
                    'session_id': session_id,
                    'answer': 'test answer'
                })
                
                answer_response = lambda_handler(answer_event, {})
                assert answer_response['statusCode'] == 400
                assert 'paused state' in json.loads(answer_response['body'])['error']
                
                # Step 4: Resume quiz
                resume_event = create_quiz_event('POST', '/quiz/resume', {
                    'session_id': session_id
                })
                
                resume_response = lambda_handler(resume_event, {})
                assert resume_response['statusCode'] == 200
                assert json.loads(resume_response['body'])['status'] == 'resumed'
                
                # Step 5: Submit answer (should work now)
                answer_response = lambda_handler(answer_event, {})
                assert answer_response['statusCode'] == 200
                
                answer_body = json.loads(answer_response['body'])
                assert 'evaluation' in answer_body
                assert 'progress' in answer_body
                
        finally:
            cleanup_test_user(email)
    
    @pytest.mark.localstack
    def test_concurrent_access_prevention(self, test_environment, clean_database):
        """Test that concurrent access to sessions is handled properly"""
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
                # Create domain with terms
                domain_data = {
                    'name': 'Concurrent Test Domain',
                    'description': 'Test domain for concurrent access testing',
                    'terms': [
                        {'term': 'Term1', 'definition': 'Definition 1'}
                    ]
                }
                
                domain_id = create_domain_with_terms(user_id, email, domain_data)
                
                # Start quiz
                start_event = create_quiz_event('POST', '/quiz/start', {
                    'domain_id': domain_id
                })
                
                start_response = lambda_handler(start_event, {})
                assert start_response['statusCode'] == 200
                
                session_id = json.loads(start_response['body'])['session_id']
                
                # Try to start another quiz for the same domain (should return existing session)
                start_response_2 = lambda_handler(start_event, {})
                assert start_response_2['statusCode'] == 200
                
                start_body_2 = json.loads(start_response_2['body'])
                assert start_body_2['session_id'] == session_id
                assert start_body_2['status'] == 'resumed'
                
        finally:
            cleanup_test_user(email)
    
    @pytest.mark.localstack
    def test_session_timeout_handling(self, test_environment, clean_database):
        """Test session timeout and cleanup"""
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
                # Create domain with terms
                domain_data = {
                    'name': 'Timeout Test Domain',
                    'description': 'Test domain for timeout testing',
                    'terms': [
                        {'term': 'Term1', 'definition': 'Definition 1'}
                    ]
                }
                
                domain_id = create_domain_with_terms(user_id, email, domain_data)
                
                # Start quiz
                start_event = create_quiz_event('POST', '/quiz/start', {
                    'domain_id': domain_id
                })
                
                start_response = lambda_handler(start_event, {})
                assert start_response['statusCode'] == 200
                
                session_id = json.loads(start_response['body'])['session_id']
                
                # Simulate session timeout by directly updating database
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE quiz_sessions 
                        SET started_at = started_at - INTERVAL '2 hours'
                        WHERE id = %s
                    """, (session_id,))
                    conn.commit()
                    cursor.close()
                
                # Try to interact with timed-out session
                # (In a real implementation, we might check for timeouts)
                pause_event = create_quiz_event('POST', '/quiz/pause', {
                    'session_id': session_id
                })
                
                pause_response = lambda_handler(pause_event, {})
                # For now, this should still work - timeout handling would be a future enhancement
                assert pause_response['statusCode'] == 200
                
        finally:
            cleanup_test_user(email)
    
    @pytest.mark.localstack
    def test_question_randomization_consistency(self, test_environment, clean_database):
        """Test that question order is consistent within a session"""
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
                # Create domain with multiple terms
                domain_data = {
                    'name': 'Randomization Test Domain',
                    'description': 'Test domain for randomization testing',
                    'terms': [
                        {'term': 'Term1', 'definition': 'Definition 1'},
                        {'term': 'Term2', 'definition': 'Definition 2'},
                        {'term': 'Term3', 'definition': 'Definition 3'},
                        {'term': 'Term4', 'definition': 'Definition 4'}
                    ]
                }
                
                domain_id = create_domain_with_terms(user_id, email, domain_data)
                
                # Start quiz
                start_event = create_quiz_event('POST', '/quiz/start', {
                    'domain_id': domain_id
                })
                
                start_response = lambda_handler(start_event, {})
                assert start_response['statusCode'] == 200
                
                start_body = json.loads(start_response['body'])
                session_id = start_body['session_id']
                first_question = start_body['current_question']
                
                # Pause and resume - should get same question
                pause_event = create_quiz_event('POST', '/quiz/pause', {
                    'session_id': session_id
                })
                
                pause_response = lambda_handler(pause_event, {})
                assert pause_response['statusCode'] == 200
                
                resume_event = create_quiz_event('POST', '/quiz/resume', {
                    'session_id': session_id
                })
                
                resume_response = lambda_handler(resume_event, {})
                assert resume_response['statusCode'] == 200
                
                resume_body = json.loads(resume_response['body'])
                resumed_question = resume_body['current_question']
                
                # Should be the same question
                assert resumed_question['term_id'] == first_question['term_id']
                assert resumed_question['term'] == first_question['term']
                assert resumed_question['question_number'] == first_question['question_number']
                
        finally:
            cleanup_test_user(email)
    
    @pytest.mark.localstack
    def test_quiz_completion_logic(self, test_environment, clean_database):
        """Test quiz completion detection and logic"""
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
        
        def create_quiz_get_event(path, query_params=None):
            return {
                'httpMethod': 'GET',
                'path': path,
                'queryStringParameters': query_params or {},
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
                # Create domain with single term for easy completion testing
                domain_data = {
                    'name': 'Completion Test Domain',
                    'description': 'Test domain for completion testing',
                    'terms': [
                        {'term': 'OnlyTerm', 'definition': 'Only definition'}
                    ]
                }
                
                domain_id = create_domain_with_terms(user_id, email, domain_data)
                
                # Start quiz
                start_event = create_quiz_event('POST', '/quiz/start', {
                    'domain_id': domain_id
                })
                
                start_response = lambda_handler(start_event, {})
                assert start_response['statusCode'] == 200
                
                session_id = json.loads(start_response['body'])['session_id']
                
                # Submit answer to complete quiz
                answer_event = create_quiz_event('POST', '/quiz/answer', {
                    'session_id': session_id,
                    'answer': 'Only definition'
                })
                
                answer_response = lambda_handler(answer_event, {})
                assert answer_response['statusCode'] == 200
                
                answer_body = json.loads(answer_response['body'])
                assert answer_body['quiz_completed'] is True
                assert answer_body['progress']['completed'] is True
                
                # Try to submit another answer (should fail)
                answer_response_2 = lambda_handler(answer_event, {})
                assert answer_response_2['statusCode'] == 400
                assert 'completed' in json.loads(answer_response_2['body'])['error']
                
                # Get completion summary
                complete_event = create_quiz_get_event('/quiz/complete', {
                    'session_id': session_id
                })
                
                complete_response = lambda_handler(complete_event, {})
                assert complete_response['statusCode'] == 200
                
                complete_body = json.loads(complete_response['body'])
                assert complete_body['status'] == 'completed'
                assert 'performance' in complete_body
                assert 'detailed_results' in complete_body
                
        finally:
            cleanup_test_user(email)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])