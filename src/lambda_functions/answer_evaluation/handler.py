"""
Answer Evaluation Lambda Function Handler
Handles semantic answer evaluation using sentence transformer model
"""
import json
import os
import logging
from typing import Dict, Any, List, Optional
from database import get_db_connection
from response_utils import create_response, handle_error
from auth_utils import extract_user_from_cognito_event
from model_utils import get_model_manager, initialize_model
from evaluation_config import EvaluationConfig, FeedbackTemplates, get_evaluation_config

logger = logging.getLogger(__name__)

# Get evaluation configuration
EVAL_CONFIG = get_evaluation_config()

# Initialize model on Lambda container startup
try:
    initialize_model()
    logger.info("Model initialized successfully on container startup")
except Exception as e:
    logger.error(f"Failed to initialize model on startup: {str(e)}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for answer evaluation operations
    """
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        # Health check endpoint (no auth required)
        if http_method == 'GET' and '/health' in path:
            return handle_health_check()
        
        # Verify authentication using Cognito authorizer context
        auth_result = extract_user_from_cognito_event(event)
        if not auth_result['valid']:
            return create_response(401, {'error': 'Unauthorized'})
        
        if http_method == 'POST':
            if '/evaluate' in path:
                return handle_evaluate_answer(event, auth_result['user_id'])
            elif '/batch-evaluate' in path:
                return handle_batch_evaluate(event, auth_result['user_id'])
        
        return create_response(404, {'error': 'Endpoint not found'})
        
    except Exception as e:
        return handle_error(e)


def handle_evaluate_answer(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle single answer evaluation"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        student_answer = body.get('student_answer', '').strip()
        correct_answer = body.get('correct_answer', '').strip()
        threshold_raw = body.get('threshold', EVAL_CONFIG['default_threshold'])
        
        # Validate threshold before converting to float
        try:
            threshold = float(threshold_raw) if threshold_raw is not None else EVAL_CONFIG['default_threshold']
        except (ValueError, TypeError):
            return create_response(400, {'error': 'threshold must be a valid number'})
        
        # Validate inputs
        if not student_answer:
            return create_response(400, {'error': 'student_answer is required'})
        
        if not correct_answer:
            return create_response(400, {'error': 'correct_answer is required'})
        
        if not EvaluationConfig.validate_threshold(threshold):
            return create_response(400, {'error': 'threshold must be between 0.0 and 1.0'})
        
        if not EvaluationConfig.validate_text_length(student_answer):
            return create_response(400, {'error': f'student_answer too long (max {EvaluationConfig.MAX_TEXT_LENGTH} characters)'})
        
        if not EvaluationConfig.validate_text_length(correct_answer):
            return create_response(400, {'error': f'correct_answer too long (max {EvaluationConfig.MAX_TEXT_LENGTH} characters)'})
        
        # Evaluate the answer
        evaluation_result = evaluate_answer(student_answer, correct_answer, threshold)
        
        if evaluation_result is None:
            return create_response(503, {'error': 'Answer evaluation service temporarily unavailable'})
        
        return create_response(200, evaluation_result)
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ValueError as e:
        return create_response(400, {'error': f'Invalid input: {str(e)}'})
    except Exception as e:
        logger.error(f"Error in handle_evaluate_answer: {str(e)}")
        return handle_error(e)


def handle_batch_evaluate(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle batch answer evaluation"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        answer_pairs = body.get('answer_pairs', [])
        threshold_raw = body.get('threshold', EVAL_CONFIG['default_threshold'])
        
        # Validate threshold before converting to float
        try:
            threshold = float(threshold_raw) if threshold_raw is not None else EVAL_CONFIG['default_threshold']
        except (ValueError, TypeError):
            return create_response(400, {'error': 'threshold must be a valid number'})
        
        # Validate inputs
        if not isinstance(answer_pairs, list):
            return create_response(400, {'error': 'answer_pairs must be a list'})
        
        if len(answer_pairs) == 0:
            return create_response(400, {'error': 'answer_pairs cannot be empty'})
        
        if len(answer_pairs) > EVAL_CONFIG['max_batch_size']:
            return create_response(400, {'error': f'batch size cannot exceed {EVAL_CONFIG["max_batch_size"]} pairs'})
        
        if not EvaluationConfig.validate_threshold(threshold):
            return create_response(400, {'error': 'threshold must be between 0.0 and 1.0'})
        
        # Validate each pair
        for i, pair in enumerate(answer_pairs):
            if not isinstance(pair, dict):
                return create_response(400, {'error': f'answer_pairs[{i}] must be an object'})
            
            if 'student_answer' not in pair or 'correct_answer' not in pair:
                return create_response(400, {'error': f'answer_pairs[{i}] must have student_answer and correct_answer'})
        
        # Evaluate all answer pairs
        results = []
        for pair in answer_pairs:
            student_answer = pair['student_answer'].strip()
            correct_answer = pair['correct_answer'].strip()
            
            evaluation_result = evaluate_answer(student_answer, correct_answer, threshold)
            results.append(evaluation_result)
        
        # Check if any evaluations failed
        failed_count = sum(1 for result in results if result is None)
        if failed_count > 0:
            logger.warning(f"Failed to evaluate {failed_count} out of {len(results)} answer pairs")
        
        return create_response(200, {
            'results': results,
            'total_pairs': len(answer_pairs),
            'successful_evaluations': len(results) - failed_count,
            'failed_evaluations': failed_count
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    except ValueError as e:
        return create_response(400, {'error': f'Invalid input: {str(e)}'})
    except Exception as e:
        logger.error(f"Error in handle_batch_evaluate: {str(e)}")
        return handle_error(e)


def handle_health_check() -> Dict[str, Any]:
    """Handle health check for the evaluation service"""
    try:
        model_manager = get_model_manager()
        
        # Get model info
        model_info = model_manager.get_model_info()
        
        # Perform health check
        is_healthy = model_manager.health_check()
        
        return create_response(200, {
            'status': 'healthy' if is_healthy else 'unhealthy',
            'model_info': model_info,
            'service': 'answer-evaluation'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return create_response(503, {
            'status': 'unhealthy',
            'error': str(e),
            'service': 'answer-evaluation'
        })


def evaluate_answer(student_answer: str, correct_answer: str, threshold: float = 0.7) -> Optional[Dict[str, Any]]:
    """
    Evaluate a student answer against the correct answer using semantic similarity
    
    Args:
        student_answer: The student's submitted answer
        correct_answer: The correct/expected answer
        threshold: Similarity threshold for determining correctness (0.6, 0.7, 0.8)
    
    Returns:
        Dictionary with evaluation results or None if evaluation fails
    """
    try:
        model_manager = get_model_manager()
        
        # Calculate semantic similarity
        similarity_score = model_manager.calculate_similarity(student_answer, correct_answer)
        
        if similarity_score is None:
            logger.error("Failed to calculate similarity score")
            return None
        
        # Determine if answer is correct based on threshold
        is_correct = similarity_score >= threshold
        
        # Generate feedback based on similarity score
        feedback = generate_feedback(similarity_score, threshold, correct_answer)
        
        return {
            'similarity_score': round(similarity_score, EVAL_CONFIG['similarity_precision']),
            'is_correct': is_correct,
            'feedback': feedback,
            'threshold': threshold,
            'correct_answer': correct_answer
        }
        
    except Exception as e:
        logger.error(f"Error evaluating answer: {str(e)}")
        return None


def generate_feedback(similarity_score: float, threshold: float, correct_answer: str) -> str:
    """
    Generate constructive feedback based on similarity score
    
    Args:
        similarity_score: Calculated similarity score (0.0 to 1.0)
        threshold: The threshold used for evaluation
        correct_answer: The correct answer for reference
    
    Returns:
        Feedback message for the student
    """
    try:
        # Get appropriate feedback template
        template_key = EvaluationConfig.get_feedback_template(similarity_score, threshold)
        
        # Generate feedback using template
        feedback = FeedbackTemplates.get_feedback(template_key, correct_answer)
        
        return feedback
    
    except Exception as e:
        logger.error(f"Error generating feedback: {str(e)}")
        return f"Your answer has been evaluated. The correct answer is: {correct_answer}"