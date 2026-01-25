"""
Unit tests for answer evaluation service edge cases
Tests empty answers, very long answers, special characters, and model loading failures
"""
import pytest
import json
import uuid
import sys
import os
from unittest.mock import patch, MagicMock
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.answer_evaluation.handler import (
    lambda_handler, evaluate_answer, generate_feedback, handle_health_check
)
from shared.model_utils import ModelManager
from shared.evaluation_config import EvaluationConfig, FeedbackTemplates


def create_mock_auth_event(body_data: dict, user_id: str = None) -> dict:
    """Create a mock API Gateway event with authentication"""
    if user_id is None:
        user_id = str(uuid.uuid4())
    
    return {
        'httpMethod': 'POST',
        'path': '/api/answer-evaluation/evaluate',
        'headers': {
            'Authorization': f'Bearer mock_token_{user_id}',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body_data),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': 'test@example.com'
                }
            }
        }
    }


def create_health_check_event() -> dict:
    """Create a health check event"""
    return {
        'httpMethod': 'GET',
        'path': '/api/answer-evaluation/health',
        'headers': {}
    }


class TestAnswerEvaluationEdgeCases:
    """Test edge cases for answer evaluation"""
    
    def test_empty_student_answer(self, test_environment):
        """Test handling of empty student answers"""
        event = create_mock_auth_event({
            'student_answer': '',
            'correct_answer': 'A serverless compute service',
            'threshold': 0.7
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'student_answer is required' in body['error']
    
    def test_whitespace_only_student_answer(self, test_environment):
        """Test handling of whitespace-only student answers"""
        event = create_mock_auth_event({
            'student_answer': '   \n\t  ',
            'correct_answer': 'A serverless compute service',
            'threshold': 0.7
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'student_answer is required' in body['error']
    
    def test_empty_correct_answer(self, test_environment):
        """Test handling of empty correct answers"""
        event = create_mock_auth_event({
            'student_answer': 'A serverless compute service',
            'correct_answer': '',
            'threshold': 0.7
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'correct_answer is required' in body['error']
    
    def test_very_long_student_answer(self, test_environment):
        """Test handling of very long student answers"""
        # Create a string longer than MAX_TEXT_LENGTH
        long_answer = 'A' * (EvaluationConfig.MAX_TEXT_LENGTH + 100)
        
        event = create_mock_auth_event({
            'student_answer': long_answer,
            'correct_answer': 'A serverless compute service',
            'threshold': 0.7
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'student_answer too long' in body['error']
    
    def test_very_long_correct_answer(self, test_environment):
        """Test handling of very long correct answers"""
        # Create a string longer than MAX_TEXT_LENGTH
        long_answer = 'A' * (EvaluationConfig.MAX_TEXT_LENGTH + 100)
        
        event = create_mock_auth_event({
            'student_answer': 'A serverless compute service',
            'correct_answer': long_answer,
            'threshold': 0.7
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'correct_answer too long' in body['error']
    
    def test_special_characters_in_answers(self, test_environment):
        """Test handling of special characters in answers"""
        special_chars_answer = "A λ-function with ∑ symbols & émojis 🚀 and <script>alert('xss')</script>"
        
        event = create_mock_auth_event({
            'student_answer': special_chars_answer,
            'correct_answer': 'A serverless compute service with special characters',
            'threshold': 0.7
        })
        
        response = lambda_handler(event, None)
        
        # Should handle special characters gracefully
        assert response['statusCode'] in [200, 503]  # 503 if model fails, 200 if succeeds
        
        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            assert 'similarity_score' in body
            assert isinstance(body['similarity_score'], (int, float))
            assert 0.0 <= body['similarity_score'] <= 1.0
    
    def test_unicode_characters_in_answers(self, test_environment):
        """Test handling of Unicode characters in answers"""
        unicode_answer = "服务器无服务计算 (serverless computing) with 中文 characters"
        
        event = create_mock_auth_event({
            'student_answer': unicode_answer,
            'correct_answer': 'Serverless computing service',
            'threshold': 0.7
        })
        
        response = lambda_handler(event, None)
        
        # Should handle Unicode characters gracefully
        assert response['statusCode'] in [200, 503]  # 503 if model fails, 200 if succeeds
    
    def test_invalid_threshold_values(self, test_environment):
        """Test handling of invalid threshold values"""
        invalid_thresholds = [-0.1, 1.1, 'invalid']  # Remove None as it should use default
        
        for threshold in invalid_thresholds:
            event = create_mock_auth_event({
                'student_answer': 'A serverless compute service',
                'correct_answer': 'A serverless compute service',
                'threshold': threshold
            })
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert 'threshold' in body['error'] or 'number' in body['error']
    
    def test_malformed_json_request(self, test_environment):
        """Test handling of malformed JSON in request body"""
        user_id = str(uuid.uuid4())
        
        event = {
            'httpMethod': 'POST',
            'path': '/api/answer-evaluation/evaluate',
            'headers': {
                'Authorization': f'Bearer mock_token_{user_id}',
                'Content-Type': 'application/json'
            },
            'body': '{"student_answer": "test", "correct_answer": "test", invalid json}',
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': 'test@example.com'
                    }
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid JSON' in body['error']
    
    def test_missing_request_body(self, test_environment):
        """Test handling of missing request body"""
        user_id = str(uuid.uuid4())
        
        event = {
            'httpMethod': 'POST',
            'path': '/api/answer-evaluation/evaluate',
            'headers': {
                'Authorization': f'Bearer mock_token_{user_id}',
                'Content-Type': 'application/json'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': 'test@example.com'
                    }
                }
            }
            # No body field
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'student_answer is required' in body['error']
    
    def test_unauthorized_request(self, test_environment):
        """Test handling of unauthorized requests"""
        event = {
            'httpMethod': 'POST',
            'path': '/api/answer-evaluation/evaluate',
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'student_answer': 'test',
                'correct_answer': 'test',
                'threshold': 0.7
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert 'Unauthorized' in body['error']
    
    def test_unsupported_http_method(self, test_environment):
        """Test handling of unsupported HTTP methods"""
        user_id = str(uuid.uuid4())
        
        event = {
            'httpMethod': 'DELETE',
            'path': '/api/answer-evaluation/evaluate',
            'headers': {
                'Authorization': f'Bearer mock_token_{user_id}',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'student_answer': 'test',
                'correct_answer': 'test',
                'threshold': 0.7
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': 'test@example.com'
                    }
                }
            }
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'Endpoint not found' in body['error']
    
    def test_health_check_endpoint(self, test_environment):
        """Test the health check endpoint"""
        event = create_health_check_event()
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] in [200, 503]  # 200 if healthy, 503 if unhealthy
        body = json.loads(response['body'])
        assert 'status' in body
        assert 'service' in body
        assert body['service'] == 'answer-evaluation'


class TestModelUtilsEdgeCases:
    """Test edge cases for model utilities"""
    
    def test_model_manager_with_invalid_path(self):
        """Test ModelManager with invalid model path"""
        manager = ModelManager(model_path='/nonexistent/path')
        
        # Should fail to load model
        assert not manager.load_model()
        
        # Should return None for encoding
        result = manager.encode_text('test text')
        assert result is None
        
        # Should return None for similarity
        similarity = manager.calculate_similarity('text1', 'text2')
        assert similarity is None
        
        # Health check should fail
        assert not manager.health_check()
    
    def test_model_manager_with_empty_text(self):
        """Test ModelManager with empty text input"""
        manager = ModelManager()
        
        # Try to load model (may fail if model not available)
        if manager.load_model():
            # Test with empty string
            result = manager.encode_text('')
            # Should handle empty text gracefully (may return None or empty embedding)
            assert result is None or (hasattr(result, 'shape') and result.shape[0] > 0)
            
            # Test similarity with empty strings
            similarity = manager.calculate_similarity('', 'test')
            assert similarity is None or (0.0 <= similarity <= 1.0)


class TestFeedbackGeneration:
    """Test feedback generation edge cases"""
    
    def test_feedback_with_extreme_scores(self):
        """Test feedback generation with extreme similarity scores"""
        correct_answer = "A serverless compute service"
        
        # Test with perfect score
        feedback = generate_feedback(1.0, 0.7, correct_answer)
        assert "Excellent" in feedback
        
        # Test with zero score
        feedback = generate_feedback(0.0, 0.7, correct_answer)
        assert correct_answer in feedback
        assert "Not quite right" in feedback
        
        # Test with score exactly at threshold
        feedback = generate_feedback(0.7, 0.7, correct_answer)
        assert "correct" in feedback.lower()
    
    def test_feedback_with_very_long_correct_answer(self):
        """Test feedback generation with very long correct answers"""
        long_correct_answer = "A" * 500  # Very long answer
        
        feedback = generate_feedback(0.3, 0.7, long_correct_answer)
        
        # Should include the long correct answer
        assert long_correct_answer in feedback
        assert len(feedback) > 500  # Should be longer due to feedback text + correct answer
    
    def test_feedback_templates_coverage(self):
        """Test that all feedback templates are accessible"""
        correct_answer = "Test answer"
        
        # Test all template keys
        template_keys = ['excellent', 'good', 'correct', 'close', 'partial', 'incorrect']
        
        for key in template_keys:
            feedback = FeedbackTemplates.get_feedback(key, correct_answer)
            assert isinstance(feedback, str)
            assert len(feedback) > 0
            
            if key in ['close', 'partial', 'incorrect']:
                assert correct_answer in feedback
    
    def test_evaluation_config_validation(self):
        """Test evaluation configuration validation methods"""
        # Test threshold validation
        assert EvaluationConfig.validate_threshold(0.5) == True
        assert EvaluationConfig.validate_threshold(0.0) == True
        assert EvaluationConfig.validate_threshold(1.0) == True
        assert EvaluationConfig.validate_threshold(-0.1) == False
        assert EvaluationConfig.validate_threshold(1.1) == False
        
        # Test text length validation
        short_text = "Short text"
        long_text = "A" * (EvaluationConfig.MAX_TEXT_LENGTH + 1)
        
        assert EvaluationConfig.validate_text_length(short_text) == True
        assert EvaluationConfig.validate_text_length(long_text) == False
        
        # Test threshold retrieval
        assert EvaluationConfig.get_threshold('strict') == 0.8
        assert EvaluationConfig.get_threshold('moderate') == 0.7
        assert EvaluationConfig.get_threshold('lenient') == 0.6
        assert EvaluationConfig.get_threshold('invalid') == 0.7  # Should default to moderate