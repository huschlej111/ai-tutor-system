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


class TestQuizStateTransitions:
    """Test quiz state transitions and edge cases"""
    
    @pytest.mark.unit
    @patch('shared.database.get_db_connection')
    def test_invalid_state_changes(self, mock_db_conn):
        """Test invalid state changes and error conditions"""
        user_id = 'test-user-123'
        email = 'test@example.com'
        
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
        
        # Test 1: Cannot pause non-existent session
        pause_event = create_quiz_event('POST', '/quiz/pause', {
            'session_id': str(uuid.uuid4())
        })
        
        pause_response = lambda_handler(pause_event, {})
        assert pause_response['statusCode'] == 404
        
        # Test 2: Cannot resume non-existent session
        resume_event = create_quiz_event('POST', '/quiz/resume', {
            'session_id': str(uuid.uuid4())
        })
        
        resume_response = lambda_handler(resume_event, {})
        assert resume_response['statusCode'] == 404
        
        # Test 3: Cannot submit answer to non-existent session
        answer_event = create_quiz_event('POST', '/quiz/answer', {
            'session_id': str(uuid.uuid4()),
            'answer': 'test answer'
        })
        
        answer_response = lambda_handler(answer_event, {})
        assert answer_response['statusCode'] == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
