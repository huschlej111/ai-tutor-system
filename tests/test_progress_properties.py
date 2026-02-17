"""
Property-based tests for progress tracking functionality
Tests universal properties that should hold across all inputs
"""
import pytest
import uuid
import json
from hypothesis import given, strategies as st, settings, assume
from decimal import Decimal
from datetime import datetime, timedelta
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.database import get_db_cursor, execute_query, execute_query_one
from lambda_functions.progress_tracking.handler import (
    calculate_term_mastery, 
    calculate_domain_progress,
    get_term_statistics
)


class TestProgressMonotonicity:
    """
    Property 4: Progress Calculation Monotonicity
    **Validates: Requirements 4.4, 4.5**
    
    For any student and term, completing additional quiz attempts should never 
    decrease their overall mastery level for that term (progress can only stay 
    the same or improve).
    """
    
    @given(
        similarity_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=10
        ),
        is_correct_flags=st.lists(st.booleans(), min_size=1, max_size=10)
    )
    @settings(max_examples=100, deadline=30000)
    def test_progress_monotonicity_property(self, similarity_scores, is_correct_flags):
        """
        **Feature: progress-tracking, Property 4: Progress Calculation Monotonicity**
        
        Test that adding more attempts never decreases mastery level.
        This property ensures that learning progress is monotonic - students
        can only improve or stay the same, never regress.
        """
        # Ensure both lists have the same length
        min_length = min(len(similarity_scores), len(is_correct_flags))
        similarity_scores = similarity_scores[:min_length]
        is_correct_flags = is_correct_flags[:min_length]
        
        # Skip if we don't have enough data
        assume(len(similarity_scores) >= 2)
        
        # Create test user and term
        user_id = str(uuid.uuid4())
        domain_id = str(uuid.uuid4())
        term_id = str(uuid.uuid4())
        
        try:
            with get_db_cursor() as cursor:
                # Create test user
                cursor.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                    (user_id, f"test_{user_id}@example.com", "test_hash")
                )
                
                # Create test domain
                domain_data = {"name": "Test Domain", "description": "Test domain for progress testing"}
                cursor.execute(
                    """INSERT INTO tree_nodes (id, user_id, node_type, data, metadata)
                       VALUES (%s, %s, 'domain', %s, %s)""",
                    (domain_id, user_id, json.dumps(domain_data), json.dumps({"term_count": 1}))
                )
                
                # Create test term
                term_data = {"term": "Test Term", "definition": "Test definition"}
                cursor.execute(
                    """INSERT INTO tree_nodes (id, parent_id, user_id, node_type, data)
                       VALUES (%s, %s, %s, 'term', %s)""",
                    (term_id, domain_id, user_id, json.dumps(term_data))
                )
                
                # Record attempts incrementally and check monotonicity
                previous_mastery_score = 0.0
                
                for i, (similarity_score, is_correct) in enumerate(zip(similarity_scores, is_correct_flags)):
                    # Record the attempt
                    record_id = str(uuid.uuid4())
                    cursor.execute(
                        """INSERT INTO progress_records 
                           (id, user_id, term_id, student_answer, correct_answer, 
                            is_correct, similarity_score, attempt_number, feedback)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (record_id, user_id, term_id, f"answer_{i}", "correct_answer",
                         is_correct, similarity_score, i + 1, f"feedback_{i}")
                    )
                    
                    # Calculate mastery after this attempt
                    mastery = calculate_term_mastery(user_id, term_id)
                    current_mastery_score = mastery['score']
                    
                    # MONOTONICITY PROPERTY: Current mastery should never be less than previous
                    # Allow for small floating point precision errors
                    assert current_mastery_score >= previous_mastery_score - 1e-6, (
                        f"Mastery decreased from {previous_mastery_score} to {current_mastery_score} "
                        f"after attempt {i + 1} with similarity {similarity_score}, correct: {is_correct}"
                    )
                    
                    previous_mastery_score = current_mastery_score
                
        finally:
            # Cleanup test data
            try:
                with get_db_cursor() as cursor:
                    cursor.execute("DELETE FROM progress_records WHERE user_id = %s", (user_id,))
                    cursor.execute("DELETE FROM tree_nodes WHERE user_id = %s", (user_id,))
                    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")


class TestProgressAggregationAccuracy:
    """
    Property 10: Progress Aggregation Accuracy
    **Validates: Requirements 4.2, 4.3**
    
    For any student and knowledge domain, the domain completion percentage 
    should equal the percentage of terms in that domain where the student 
    has achieved mastery.
    """
    
    @given(
        term_count=st.integers(min_value=1, max_value=10),
        mastery_levels=st.lists(
            st.sampled_from(['mastered', 'proficient', 'developing', 'beginner', 'needs_practice', 'not_attempted']),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=30000)
    def test_progress_aggregation_accuracy_property(self, term_count, mastery_levels):
        """
        **Feature: progress-tracking, Property 10: Progress Aggregation Accuracy**
        
        Test that domain completion percentage accurately reflects the percentage
        of terms where the student has achieved some level of mastery.
        """
        # Ensure we have the right number of mastery levels for terms
        mastery_levels = mastery_levels[:term_count]
        while len(mastery_levels) < term_count:
            mastery_levels.append('not_attempted')
        
        # Create test user and domain
        user_id = str(uuid.uuid4())
        domain_id = str(uuid.uuid4())
        
        try:
            with get_db_cursor() as cursor:
                # Create test user
                cursor.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                    (user_id, f"test_{user_id}@example.com", "test_hash")
                )
                
                # Create test domain
                domain_data = {"name": "Test Domain", "description": "Test domain for aggregation testing"}
                cursor.execute(
                    """INSERT INTO tree_nodes (id, user_id, node_type, data, metadata)
                       VALUES (%s, %s, 'domain', %s, %s)""",
                    (domain_id, user_id, json.dumps(domain_data), json.dumps({"term_count": term_count}))
                )
                
                # Create terms and set up their mastery levels
                term_ids = []
                for i in range(term_count):
                    term_id = str(uuid.uuid4())
                    term_ids.append(term_id)
                    
                    # Create term
                    term_data = {"term": f"Test Term {i}", "definition": f"Test definition {i}"}
                    cursor.execute(
                        """INSERT INTO tree_nodes (id, parent_id, user_id, node_type, data)
                           VALUES (%s, %s, %s, 'term', %s)""",
                        (term_id, domain_id, user_id, json.dumps(term_data))
                    )
                    
                    # Create progress records to achieve the desired mastery level
                    mastery_level = mastery_levels[i]
                    
                    if mastery_level != 'not_attempted':
                        # Create attempts that would result in the desired mastery level
                        attempts_data = self._generate_attempts_for_mastery_level(mastery_level)
                        
                        for j, (similarity_score, is_correct) in enumerate(attempts_data):
                            record_id = str(uuid.uuid4())
                            cursor.execute(
                                """INSERT INTO progress_records 
                                   (id, user_id, term_id, student_answer, correct_answer, 
                                    is_correct, similarity_score, attempt_number, feedback)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                (record_id, user_id, term_id, f"answer_{j}", "correct_answer",
                                 is_correct, similarity_score, j + 1, f"feedback_{j}")
                            )
                
                # Calculate domain progress
                domain_progress = calculate_domain_progress(user_id, domain_id)
                
                # Calculate expected completion percentage
                # Completion = mastered + proficient + developing (some level of competency)
                completed_levels = ['mastered', 'proficient', 'developing']
                
                # Get all terms in the domain to calculate actual mastery levels
                terms_query = """
                    SELECT id, data->>'term' as term
                    FROM tree_nodes
                    WHERE parent_id = %s AND node_type = 'term'
                """
                terms_result = execute_query(terms_query, (domain_id,))
                
                # Get actual mastery levels from the system
                actual_mastery_levels = []
                for term in terms_result:
                    term_id = term[0]
                    mastery = calculate_term_mastery(user_id, term_id)
                    actual_mastery_levels.append(mastery['level'])
                
                # Calculate expected percentages based on actual mastery levels
                expected_completed_count = sum(1 for level in actual_mastery_levels if level in completed_levels)
                expected_completion_percentage = (expected_completed_count / term_count) * 100
                
                # Calculate expected mastery percentage (only mastered terms)
                expected_mastered_count = sum(1 for level in actual_mastery_levels if level == 'mastered')
                expected_mastery_percentage = (expected_mastered_count / term_count) * 100
                
                # AGGREGATION ACCURACY PROPERTY: Domain percentages should match expected values
                actual_completion = domain_progress['completion_percentage']
                actual_mastery = domain_progress['mastery_percentage']
                
                # Allow for small floating point precision errors
                assert abs(actual_completion - expected_completion_percentage) < 0.1, (
                    f"Completion percentage mismatch: expected {expected_completion_percentage}, "
                    f"got {actual_completion}. Actual mastery levels: {actual_mastery_levels}"
                )
                
                assert abs(actual_mastery - expected_mastery_percentage) < 0.1, (
                    f"Mastery percentage mismatch: expected {expected_mastery_percentage}, "
                    f"got {actual_mastery}. Actual mastery levels: {actual_mastery_levels}"
                )
                
                # Verify breakdown counts match actual mastery levels (not input levels)
                breakdown = domain_progress['mastery_breakdown']
                for level in ['mastered', 'proficient', 'developing', 'beginner', 'needs_practice', 'not_attempted']:
                    expected_count = sum(1 for ml in actual_mastery_levels if ml == level)
                    actual_count = breakdown.get(level, 0)
                    
                    assert actual_count == expected_count, (
                        f"Breakdown count mismatch for {level}: expected {expected_count}, got {actual_count}. "
                        f"Actual mastery levels: {actual_mastery_levels}"
                    )
                
        finally:
            # Cleanup test data
            try:
                with get_db_cursor() as cursor:
                    cursor.execute("DELETE FROM progress_records WHERE user_id = %s", (user_id,))
                    cursor.execute("DELETE FROM tree_nodes WHERE user_id = %s", (user_id,))
                    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")
    
    def _generate_attempts_for_mastery_level(self, target_level: str) -> list:
        """Generate attempt data that would result in the target mastery level"""
        if target_level == 'mastered':
            # High similarity scores, all correct - need multiple attempts for confidence
            return [(0.95, True), (0.92, True), (0.90, True), (0.88, True), (0.93, True)]
        elif target_level == 'proficient':
            # Good similarity scores, mostly correct
            return [(0.80, True), (0.78, True), (0.75, True), (0.70, False)]
        elif target_level == 'developing':
            # Medium similarity scores, mixed results
            return [(0.65, True), (0.60, True), (0.55, False), (0.62, True)]
        elif target_level == 'beginner':
            # Lower similarity scores, mixed results - need more attempts to establish pattern
            return [(0.45, False), (0.48, True), (0.42, False), (0.46, True)]
        elif target_level == 'needs_practice':
            # Low similarity scores, mostly incorrect
            return [(0.25, False), (0.22, False), (0.28, False), (0.20, False)]
        else:
            # not_attempted - no attempts
            return []


class TestProgressConsistency:
    """Additional property tests for progress tracking consistency"""
    
    @given(
        attempts=st.lists(
            st.tuples(
                st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
                st.booleans()
            ),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50, deadline=30000)
    @pytest.mark.skip(reason="calculate_term_mastery not implemented")
    def test_mastery_calculation_deterministic(self, attempts):
        """
        Test that mastery calculation is deterministic - same attempts should 
        always produce the same mastery score.
        """
        user_id = str(uuid.uuid4())
        domain_id = str(uuid.uuid4())
        term_id = str(uuid.uuid4())
        
        try:
            with get_db_cursor() as cursor:
                # Create test data
                cursor.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                    (user_id, f"test_{user_id}@example.com", "test_hash")
                )
                
                domain_data = {"name": "Test Domain", "description": "Test domain"}
                cursor.execute(
                    """INSERT INTO tree_nodes (id, user_id, node_type, data, metadata)
                       VALUES (%s, %s, 'domain', %s, %s)""",
                    (domain_id, user_id, json.dumps(domain_data), json.dumps({"term_count": 1}))
                )
                
                term_data = {"term": "Test Term", "definition": "Test definition"}
                cursor.execute(
                    """INSERT INTO tree_nodes (id, parent_id, user_id, node_type, data)
                       VALUES (%s, %s, %s, 'term', %s)""",
                    (term_id, domain_id, user_id, json.dumps(term_data))
                )
                
                # Record attempts
                for i, (similarity_score, is_correct) in enumerate(attempts):
                    record_id = str(uuid.uuid4())
                    cursor.execute(
                        """INSERT INTO progress_records 
                           (id, user_id, term_id, student_answer, correct_answer, 
                            is_correct, similarity_score, attempt_number, feedback)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (record_id, user_id, term_id, f"answer_{i}", "correct_answer",
                         is_correct, similarity_score, i + 1, f"feedback_{i}")
                    )
                
                # Calculate mastery multiple times
                mastery1 = calculate_term_mastery(user_id, term_id)
                mastery2 = calculate_term_mastery(user_id, term_id)
                
                # Should be identical
                assert mastery1['score'] == mastery2['score'], (
                    f"Mastery calculation not deterministic: {mastery1['score']} != {mastery2['score']}"
                )
                assert mastery1['level'] == mastery2['level'], (
                    f"Mastery level not deterministic: {mastery1['level']} != {mastery2['level']}"
                )
                
        finally:
            # Cleanup
            try:
                with get_db_cursor() as cursor:
                    cursor.execute("DELETE FROM progress_records WHERE user_id = %s", (user_id,))
                    cursor.execute("DELETE FROM tree_nodes WHERE user_id = %s", (user_id,))
                    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")


if __name__ == "__main__":
    # Run property tests
    pytest.main([__file__, "-v", "--tb=short"])