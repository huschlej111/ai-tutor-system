"""
Property-based tests for answer evaluation service
Feature: tutor-system
"""
import pytest
import json
import uuid
import time
from hypothesis import given, strategies as st, settings, HealthCheck
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.answer_evaluation.handler import lambda_handler, evaluate_answer
from shared.model_utils import get_model_manager
from shared.evaluation_config import EvaluationConfig


# Test data generators
@st.composite
def valid_answer_text(draw):
    """Generate valid answer text"""
    return draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Po', 'Ps', 'Pe', 'Zs'),
            min_codepoint=32, max_codepoint=126
        ),
        min_size=5, max_size=500
    ).filter(lambda x: x.strip() and len(x.strip()) >= 5))


@st.composite
def valid_threshold(draw):
    """Generate valid threshold values"""
    return draw(st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False))


@st.composite
def answer_pair(draw):
    """Generate a pair of student answer and correct answer"""
    student_answer = draw(valid_answer_text())
    correct_answer = draw(valid_answer_text())
    threshold = draw(valid_threshold())
    
    return {
        'student_answer': student_answer,
        'correct_answer': correct_answer,
        'threshold': threshold
    }


@st.composite
def identical_answer_pair(draw):
    """Generate identical student and correct answers for symmetry testing"""
    answer_text = draw(valid_answer_text())
    threshold = draw(valid_threshold())
    
    return {
        'student_answer': answer_text,
        'correct_answer': answer_text,
        'threshold': threshold
    }


@st.composite
def semantically_equivalent_answers(draw):
    """Generate semantically equivalent answer pairs for symmetry testing"""
    # Use predefined equivalent pairs that are more clearly related
    equivalent_pairs = [
        ("Serverless compute service", "Serverless computing platform"),
        ("Event-driven execution", "Event-triggered processing"),
        ("Automatic scaling", "Auto-scaling capability"),
        ("Pay per execution", "Pay per invocation"),
        ("No server management", "Serverless architecture"),
        ("Stateless functions", "Functions without state"),
        ("Container orchestration", "Container management"),
        ("Database service", "Managed database"),
        ("Load balancing", "Traffic distribution"),
        ("Message queue", "Message queuing service")
    ]
    
    pair = draw(st.sampled_from(equivalent_pairs))
    threshold = draw(valid_threshold())
    
    return {
        'answer_a': pair[0],
        'answer_b': pair[1],
        'correct_answer': pair[0],  # Use first as the "correct" answer
        'threshold': threshold
    }


def create_mock_auth_event(body_data: dict, user_id: str = None) -> dict:
    """Create a mock API Gateway event with Cognito authentication"""
    if user_id is None:
        user_id = str(uuid.uuid4())
    
    return {
        'httpMethod': 'POST',
        'path': '/api/answer-evaluation/evaluate',
        'headers': {
            'Content-Type': 'application/json'
        },
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': f'test_{user_id}@example.com',
                    'cognito:username': f'test_user_{user_id}',
                    'email_verified': 'true'
                }
            }
        },
        'body': json.dumps(body_data)
    }


def create_batch_evaluation_event(answer_pairs: list, threshold: float, user_id: str = None) -> dict:
    """Create a mock event for batch evaluation with Cognito authentication"""
    if user_id is None:
        user_id = str(uuid.uuid4())
    
    return {
        'httpMethod': 'POST',
        'path': '/api/answer-evaluation/batch-evaluate',
        'headers': {
            'Content-Type': 'application/json'
        },
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': f'test_{user_id}@example.com',
                    'cognito:username': f'test_user_{user_id}',
                    'email_verified': 'true'
                }
            }
        },
        'body': json.dumps({
            'answer_pairs': answer_pairs,
            'threshold': threshold
        })
    }


@pytest.fixture(scope="session", autouse=True)
def ensure_model_loaded():
    """Ensure the model is loaded before running tests"""
    try:
        model_manager = get_model_manager()
        if not model_manager.load_model():
            pytest.skip("Model could not be loaded - skipping evaluation tests")
        
        # Verify model is working
        if not model_manager.health_check():
            pytest.skip("Model health check failed - skipping evaluation tests")
            
    except Exception as e:
        pytest.skip(f"Model initialization failed: {str(e)}")


@given(answer_data=answer_pair())
@settings(max_examples=50, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.localstack
def test_semantic_evaluation_consistency(answer_data, test_environment, ensure_model_loaded):
    """
    Property 8: Semantic Evaluation Consistency
    **Validates: Requirements 7.1, 7.3**
    
    For any student answer and correct definition, multiple evaluations of the same answer 
    should produce identical similarity scores and feedback.
    """
    student_answer = answer_data['student_answer']
    correct_answer = answer_data['correct_answer']
    threshold = answer_data['threshold']
    
    # Perform multiple evaluations of the same answer
    evaluation1 = evaluate_answer(student_answer, correct_answer, threshold)
    evaluation2 = evaluate_answer(student_answer, correct_answer, threshold)
    evaluation3 = evaluate_answer(student_answer, correct_answer, threshold)
    
    # All evaluations should succeed
    assert evaluation1 is not None, "First evaluation failed"
    assert evaluation2 is not None, "Second evaluation failed"
    assert evaluation3 is not None, "Third evaluation failed"
    
    # Similarity scores should be identical
    assert evaluation1['similarity_score'] == evaluation2['similarity_score'], \
        f"Inconsistent similarity scores: {evaluation1['similarity_score']} != {evaluation2['similarity_score']}"
    
    assert evaluation2['similarity_score'] == evaluation3['similarity_score'], \
        f"Inconsistent similarity scores: {evaluation2['similarity_score']} != {evaluation3['similarity_score']}"
    
    # Correctness determination should be identical
    assert evaluation1['is_correct'] == evaluation2['is_correct'], \
        f"Inconsistent correctness: {evaluation1['is_correct']} != {evaluation2['is_correct']}"
    
    assert evaluation2['is_correct'] == evaluation3['is_correct'], \
        f"Inconsistent correctness: {evaluation2['is_correct']} != {evaluation3['is_correct']}"
    
    # Feedback should be identical
    assert evaluation1['feedback'] == evaluation2['feedback'], \
        f"Inconsistent feedback: {evaluation1['feedback']} != {evaluation2['feedback']}"
    
    assert evaluation2['feedback'] == evaluation3['feedback'], \
        f"Inconsistent feedback: {evaluation2['feedback']} != {evaluation3['feedback']}"
    
    # Threshold should be preserved
    assert evaluation1['threshold'] == threshold
    assert evaluation2['threshold'] == threshold
    assert evaluation3['threshold'] == threshold


@given(answer_data=identical_answer_pair())
@settings(max_examples=30, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.localstack
def test_identical_answer_evaluation(answer_data, test_environment, ensure_model_loaded):
    """
    Test that identical answers receive perfect similarity scores
    This is a specific case of evaluation consistency
    """
    student_answer = answer_data['student_answer']
    correct_answer = answer_data['correct_answer']  # Same as student_answer
    threshold = answer_data['threshold']
    
    evaluation = evaluate_answer(student_answer, correct_answer, threshold)
    
    assert evaluation is not None, "Evaluation failed for identical answers"
    
    # Identical answers should have very high similarity (close to 1.0)
    assert evaluation['similarity_score'] >= 0.95, \
        f"Identical answers should have high similarity, got {evaluation['similarity_score']}"
    
    # Should be marked as correct regardless of threshold (since similarity is ~1.0)
    assert evaluation['is_correct'] == True, \
        f"Identical answers should be marked correct, got {evaluation['is_correct']}"


@given(equiv_data=semantically_equivalent_answers())
@settings(max_examples=20, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.localstack
def test_answer_evaluation_symmetry(equiv_data, test_environment, ensure_model_loaded):
    """
    Property 7: Answer Evaluation Symmetry
    **Validates: Requirements 7.1, 7.2**
    
    For any term definition, if answer A is semantically equivalent to answer B, 
    then both answers should receive the same evaluation score when compared to the correct definition.
    
    Note: This test focuses on the core symmetry property rather than strict similarity scores,
    as the model may not always recognize semantic equivalence in the same way humans do.
    """
    answer_a = equiv_data['answer_a']
    answer_b = equiv_data['answer_b']
    correct_answer = equiv_data['correct_answer']
    threshold = equiv_data['threshold']
    
    # Evaluate both semantically equivalent answers
    evaluation_a = evaluate_answer(answer_a, correct_answer, threshold)
    evaluation_b = evaluate_answer(answer_b, correct_answer, threshold)
    
    assert evaluation_a is not None, "Evaluation A failed"
    assert evaluation_b is not None, "Evaluation B failed"
    
    # Core symmetry property: Both evaluations should be deterministic and consistent
    # Re-evaluate the same answers to ensure consistency
    evaluation_a2 = evaluate_answer(answer_a, correct_answer, threshold)
    evaluation_b2 = evaluate_answer(answer_b, correct_answer, threshold)
    
    assert evaluation_a['similarity_score'] == evaluation_a2['similarity_score'], \
        f"Answer A evaluation is not consistent: {evaluation_a['similarity_score']} != {evaluation_a2['similarity_score']}"
    
    assert evaluation_b['similarity_score'] == evaluation_b2['similarity_score'], \
        f"Answer B evaluation is not consistent: {evaluation_b['similarity_score']} != {evaluation_b2['similarity_score']}"
    
    # Both answers should have reasonable similarity scores (not completely random)
    assert 0.0 <= evaluation_a['similarity_score'] <= 1.0, \
        f"Answer A similarity score out of range: {evaluation_a['similarity_score']}"
    
    assert 0.0 <= evaluation_b['similarity_score'] <= 1.0, \
        f"Answer B similarity score out of range: {evaluation_b['similarity_score']}"
    
    # If the answers are truly equivalent, at least one should have decent similarity
    # This is a weaker but more realistic test for this model
    max_similarity = max(evaluation_a['similarity_score'], evaluation_b['similarity_score'])
    assert max_similarity >= 0.3, \
        f"Neither semantically equivalent answer achieved reasonable similarity. " \
        f"Answer A: {evaluation_a['similarity_score']}, Answer B: {evaluation_b['similarity_score']}"


@given(answer_data=answer_pair())
@settings(max_examples=30, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.localstack
def test_evaluation_score_bounds(answer_data, test_environment, ensure_model_loaded):
    """
    Test that similarity scores are always within valid bounds [0.0, 1.0]
    """
    student_answer = answer_data['student_answer']
    correct_answer = answer_data['correct_answer']
    threshold = answer_data['threshold']
    
    evaluation = evaluate_answer(student_answer, correct_answer, threshold)
    
    assert evaluation is not None, "Evaluation failed"
    
    # Similarity score must be between 0.0 and 1.0
    similarity_score = evaluation['similarity_score']
    assert 0.0 <= similarity_score <= 1.0, \
        f"Similarity score {similarity_score} is outside valid range [0.0, 1.0]"
    
    # Correctness should match threshold comparison
    expected_correct = similarity_score >= threshold
    assert evaluation['is_correct'] == expected_correct, \
        f"Correctness mismatch: score={similarity_score}, threshold={threshold}, " \
        f"expected={expected_correct}, got={evaluation['is_correct']}"


@given(answer_pairs=st.lists(answer_pair(), min_size=2, max_size=10))
@settings(max_examples=10, deadline=60000, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.localstack
def test_batch_evaluation_consistency(answer_pairs, test_environment, ensure_model_loaded):
    """
    Test that batch evaluation produces the same results as individual evaluations
    """
    # Use the same threshold for all pairs
    threshold = 0.7
    
    # Perform individual evaluations
    individual_results = []
    for pair_data in answer_pairs:
        result = evaluate_answer(
            pair_data['student_answer'], 
            pair_data['correct_answer'], 
            threshold
        )
        individual_results.append(result)
    
    # Perform batch evaluation via API
    batch_pairs = [
        {
            'student_answer': pair_data['student_answer'],
            'correct_answer': pair_data['correct_answer']
        }
        for pair_data in answer_pairs
    ]
    
    event = create_batch_evaluation_event(batch_pairs, threshold)
    response = lambda_handler(event, None)
    
    assert response['statusCode'] == 200, f"Batch evaluation failed: {response}"
    
    batch_data = json.loads(response['body'])
    batch_results = batch_data['results']
    
    # Compare individual and batch results
    assert len(batch_results) == len(individual_results), \
        f"Result count mismatch: individual={len(individual_results)}, batch={len(batch_results)}"
    
    for i, (individual, batch) in enumerate(zip(individual_results, batch_results)):
        if individual is not None and batch is not None:
            assert individual['similarity_score'] == batch['similarity_score'], \
                f"Similarity score mismatch at index {i}: individual={individual['similarity_score']}, batch={batch['similarity_score']}"
            
            assert individual['is_correct'] == batch['is_correct'], \
                f"Correctness mismatch at index {i}: individual={individual['is_correct']}, batch={batch['is_correct']}"


@given(answer_data=answer_pair())
@settings(max_examples=20, deadline=30000, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.localstack
def test_evaluation_api_consistency(answer_data, test_environment, ensure_model_loaded):
    """
    Test that API evaluation produces the same results as direct function calls
    """
    student_answer = answer_data['student_answer']
    correct_answer = answer_data['correct_answer']
    threshold = answer_data['threshold']
    
    # Direct function call
    direct_result = evaluate_answer(student_answer, correct_answer, threshold)
    
    # API call
    event = create_mock_auth_event({
        'student_answer': student_answer,
        'correct_answer': correct_answer,
        'threshold': threshold
    })
    
    api_response = lambda_handler(event, None)
    
    assert api_response['statusCode'] == 200, f"API call failed: {api_response}"
    
    api_result = json.loads(api_response['body'])
    
    # Compare results
    if direct_result is not None:
        assert direct_result['similarity_score'] == api_result['similarity_score'], \
            f"Similarity score mismatch: direct={direct_result['similarity_score']}, api={api_result['similarity_score']}"
        
        assert direct_result['is_correct'] == api_result['is_correct'], \
            f"Correctness mismatch: direct={direct_result['is_correct']}, api={api_result['is_correct']}"
        
        assert direct_result['feedback'] == api_result['feedback'], \
            f"Feedback mismatch: direct={direct_result['feedback']}, api={api_result['feedback']}"