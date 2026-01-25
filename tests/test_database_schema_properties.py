"""
Property-based tests for database schema integrity
**Property 5: Data Persistence Round Trip**
**Validates: Requirements 5.1, 5.2**
"""
import pytest
import uuid
import json
import os
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
import psycopg2
from psycopg2.extras import RealDictCursor

# Set environment variables for local testing
os.environ.update({
    'DB_HOST': 'localhost',
    'DB_PORT': '5432',
    'DB_NAME': 'tutor_system',
    'DB_USER': 'tutor_user',
    'DB_PASSWORD': 'tutor_password'
})

# Import shared modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))

from src.shared.database import get_db_connection, get_db_cursor, health_check


# Test data generators using Hypothesis strategies
@composite
def user_data(draw):
    """Generate valid user data"""
    # Use printable ASCII characters to avoid Unicode encoding issues
    safe_text = st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126))
    
    return {
        'email': draw(st.emails()),
        'password_hash': draw(safe_text.filter(lambda x: len(x) >= 10 and len(x) <= 255)),
        'first_name': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 100)),
        'last_name': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 100)),
        'is_active': draw(st.booleans()),
        'is_verified': draw(st.booleans())
    }


@composite
def domain_data(draw):
    """Generate valid domain node data"""
    # Use printable ASCII characters to avoid Unicode encoding issues
    safe_text = st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126))
    
    return {
        'name': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 255)),
        'description': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 1000)),
        'subject': draw(st.sampled_from(['AWS', 'Python', 'JavaScript', 'DevOps', 'Security'])),
        'difficulty': draw(st.sampled_from(['beginner', 'intermediate', 'advanced'])),
        'tags': draw(st.lists(safe_text.filter(lambda x: len(x) >= 1 and len(x) <= 50), min_size=0, max_size=10))
    }


@composite
def term_data(draw):
    """Generate valid term node data"""
    # Use printable ASCII characters to avoid Unicode encoding issues
    safe_text = st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126))
    
    return {
        'term': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 255)),
        'definition': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 2000)),
        'examples': draw(st.lists(safe_text.filter(lambda x: len(x) >= 1 and len(x) <= 500), min_size=0, max_size=5)),
        'difficulty': draw(st.integers(min_value=1, max_value=5)),
        'category': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 100))
    }


@composite
def quiz_session_data(draw):
    """Generate valid quiz session data"""
    return {
        'status': draw(st.sampled_from(['active', 'paused', 'completed', 'abandoned'])),
        'current_term_index': draw(st.integers(min_value=0, max_value=100)),
        'total_questions': draw(st.integers(min_value=0, max_value=100)),
        'correct_answers': draw(st.integers(min_value=0, max_value=100))
    }


@composite
def progress_record_data(draw):
    """Generate valid progress record data"""
    # Use printable ASCII characters to avoid Unicode encoding issues
    safe_text = st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126))
    
    return {
        'student_answer': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 2000)),
        'correct_answer': draw(safe_text.filter(lambda x: len(x.strip()) >= 1 and len(x) <= 2000)),
        'is_correct': draw(st.booleans()),
        'similarity_score': draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        'attempt_number': draw(st.integers(min_value=1, max_value=10)),
        'feedback': draw(safe_text.filter(lambda x: len(x) <= 1000))
    }


class TestDatabaseSchemaProperties:
    """Property-based tests for database schema integrity"""
    
    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Ensure database is available for testing"""
        assert health_check(), "Database connection failed"
        
        # Clean up test data before each test (in correct order due to foreign keys)
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Delete in reverse dependency order to avoid foreign key violations
                cursor.execute("DELETE FROM progress_records WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
                cursor.execute("DELETE FROM quiz_sessions WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
                cursor.execute("DELETE FROM batch_uploads WHERE admin_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
                cursor.execute("DELETE FROM tree_nodes WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
                cursor.execute("DELETE FROM users WHERE email LIKE 'test_%'")
                conn.commit()
        
        yield
        
        # Clean up test data after each test as well
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Delete in reverse dependency order to avoid foreign key violations
                cursor.execute("DELETE FROM progress_records WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
                cursor.execute("DELETE FROM quiz_sessions WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
                cursor.execute("DELETE FROM batch_uploads WHERE admin_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
                cursor.execute("DELETE FROM tree_nodes WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%')")
                cursor.execute("DELETE FROM users WHERE email LIKE 'test_%'")
                conn.commit()
    
    @given(user_data())
    @settings(max_examples=100, deadline=5000)
    def test_user_data_persistence_round_trip(self, user_data_dict):
        """
        Property 5: Data Persistence Round Trip - Users
        For any valid user data, storing then retrieving should produce equivalent data
        **Validates: Requirements 5.1, 5.2**
        """
        # Make email unique for this test
        user_data_dict['email'] = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Insert user data
                cursor.execute("""
                    INSERT INTO users (email, password_hash, first_name, last_name, is_active, is_verified)
                    VALUES (%(email)s, %(password_hash)s, %(first_name)s, %(last_name)s, %(is_active)s, %(is_verified)s)
                    RETURNING id, email, password_hash, first_name, last_name, is_active, is_verified
                """, user_data_dict)
                
                inserted_user = dict(cursor.fetchone())
                user_id = inserted_user['id']
                
                # Retrieve user data
                cursor.execute("""
                    SELECT id, email, password_hash, first_name, last_name, is_active, is_verified
                    FROM users WHERE id = %s
                """, (user_id,))
                
                retrieved_user = dict(cursor.fetchone())
                
                # Verify round trip integrity
                assert retrieved_user['email'] == user_data_dict['email']
                assert retrieved_user['password_hash'] == user_data_dict['password_hash']
                assert retrieved_user['first_name'] == user_data_dict['first_name']
                assert retrieved_user['last_name'] == user_data_dict['last_name']
                assert retrieved_user['is_active'] == user_data_dict['is_active']
                assert retrieved_user['is_verified'] == user_data_dict['is_verified']
                
                conn.commit()
    
    @given(domain_data())
    @settings(max_examples=100, deadline=5000)
    def test_tree_nodes_domain_persistence_round_trip(self, domain_data_dict):
        """
        Property 5: Data Persistence Round Trip - Domain Nodes
        For any valid domain data, storing then retrieving should produce equivalent JSONB data
        **Validates: Requirements 5.1, 5.2, 6.2**
        """
        # Create test user first
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Create user
                cursor.execute("""
                    INSERT INTO users (email, password_hash, first_name, last_name)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (test_email, 'test_hash', 'Test', 'User'))
                
                user_id = cursor.fetchone()['id']
                
                # Insert domain node
                cursor.execute("""
                    INSERT INTO tree_nodes (user_id, node_type, data, metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, user_id, node_type, data, metadata
                """, (user_id, 'domain', json.dumps(domain_data_dict), json.dumps({'test': True})))
                
                inserted_node = dict(cursor.fetchone())
                node_id = inserted_node['id']
                
                # Retrieve domain node
                cursor.execute("""
                    SELECT id, user_id, node_type, data, metadata
                    FROM tree_nodes WHERE id = %s
                """, (node_id,))
                
                retrieved_node = dict(cursor.fetchone())
                
                # Verify round trip integrity
                assert retrieved_node['user_id'] == user_id
                assert retrieved_node['node_type'] == 'domain'
                
                # Verify JSONB data integrity
                retrieved_data = retrieved_node['data']
                assert retrieved_data['name'] == domain_data_dict['name']
                assert retrieved_data['description'] == domain_data_dict['description']
                assert retrieved_data['subject'] == domain_data_dict['subject']
                assert retrieved_data['difficulty'] == domain_data_dict['difficulty']
                assert retrieved_data['tags'] == domain_data_dict['tags']
                
                conn.commit()
    
    @given(term_data())
    @settings(max_examples=100, deadline=5000)
    def test_tree_nodes_term_persistence_round_trip(self, term_data_dict):
        """
        Property 5: Data Persistence Round Trip - Term Nodes
        For any valid term data, storing then retrieving should preserve hierarchical relationships
        **Validates: Requirements 5.1, 5.2, 6.4**
        """
        # Create test user and domain first
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Create user
                cursor.execute("""
                    INSERT INTO users (email, password_hash, first_name, last_name)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (test_email, 'test_hash', 'Test', 'User'))
                
                user_id = cursor.fetchone()['id']
                
                # Create domain node
                domain_data = {'name': 'Test Domain', 'description': 'Test Description'}
                cursor.execute("""
                    INSERT INTO tree_nodes (user_id, node_type, data)
                    VALUES (%s, %s, %s) RETURNING id
                """, (user_id, 'domain', json.dumps(domain_data)))
                
                domain_id = cursor.fetchone()['id']
                
                # Insert term node
                cursor.execute("""
                    INSERT INTO tree_nodes (parent_id, user_id, node_type, data)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, parent_id, user_id, node_type, data
                """, (domain_id, user_id, 'term', json.dumps(term_data_dict)))
                
                inserted_term = dict(cursor.fetchone())
                term_id = inserted_term['id']
                
                # Retrieve term with parent relationship
                cursor.execute("""
                    SELECT t.id, t.parent_id, t.user_id, t.node_type, t.data,
                           p.data as parent_data
                    FROM tree_nodes t
                    LEFT JOIN tree_nodes p ON p.id = t.parent_id
                    WHERE t.id = %s
                """, (term_id,))
                
                retrieved_term = dict(cursor.fetchone())
                
                # Verify round trip integrity
                assert retrieved_term['parent_id'] == domain_id
                assert retrieved_term['user_id'] == user_id
                assert retrieved_term['node_type'] == 'term'
                
                # Verify JSONB data integrity
                retrieved_data = retrieved_term['data']
                assert retrieved_data['term'] == term_data_dict['term']
                assert retrieved_data['definition'] == term_data_dict['definition']
                assert retrieved_data['examples'] == term_data_dict['examples']
                assert retrieved_data['difficulty'] == term_data_dict['difficulty']
                assert retrieved_data['category'] == term_data_dict['category']
                
                # Verify parent relationship
                parent_data = retrieved_term['parent_data']
                assert parent_data['name'] == 'Test Domain'
                
                conn.commit()
    
    @given(quiz_session_data())
    @settings(max_examples=100, deadline=5000)
    def test_quiz_session_persistence_round_trip(self, session_data_dict):
        """
        Property 5: Data Persistence Round Trip - Quiz Sessions
        For any valid quiz session data, storing then retrieving should preserve session state
        **Validates: Requirements 5.1, 5.2**
        """
        # Ensure correct_answers <= total_questions
        if session_data_dict['correct_answers'] > session_data_dict['total_questions']:
            session_data_dict['correct_answers'] = session_data_dict['total_questions']
        
        # Create test user and domain first
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Create user
                cursor.execute("""
                    INSERT INTO users (email, password_hash, first_name, last_name)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (test_email, 'test_hash', 'Test', 'User'))
                
                user_id = cursor.fetchone()['id']
                
                # Create domain node
                domain_data = {'name': 'Test Domain', 'description': 'Test Description'}
                cursor.execute("""
                    INSERT INTO tree_nodes (user_id, node_type, data)
                    VALUES (%s, %s, %s) RETURNING id
                """, (user_id, 'domain', json.dumps(domain_data)))
                
                domain_id = cursor.fetchone()['id']
                
                # Insert quiz session
                cursor.execute("""
                    INSERT INTO quiz_sessions 
                    (user_id, domain_id, status, current_term_index, total_questions, correct_answers)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, domain_id, status, current_term_index, total_questions, correct_answers
                """, (
                    user_id, domain_id, session_data_dict['status'],
                    session_data_dict['current_term_index'], session_data_dict['total_questions'],
                    session_data_dict['correct_answers']
                ))
                
                inserted_session = dict(cursor.fetchone())
                session_id = inserted_session['id']
                
                # Retrieve quiz session
                cursor.execute("""
                    SELECT id, user_id, domain_id, status, current_term_index, total_questions, correct_answers
                    FROM quiz_sessions WHERE id = %s
                """, (session_id,))
                
                retrieved_session = dict(cursor.fetchone())
                
                # Verify round trip integrity
                assert retrieved_session['user_id'] == user_id
                assert retrieved_session['domain_id'] == domain_id
                assert retrieved_session['status'] == session_data_dict['status']
                assert retrieved_session['current_term_index'] == session_data_dict['current_term_index']
                assert retrieved_session['total_questions'] == session_data_dict['total_questions']
                assert retrieved_session['correct_answers'] == session_data_dict['correct_answers']
                
                conn.commit()
    
    @given(progress_record_data())
    @settings(max_examples=100, deadline=5000)
    def test_progress_record_persistence_round_trip(self, progress_data_dict):
        """
        Property 5: Data Persistence Round Trip - Progress Records
        For any valid progress data, storing then retrieving should preserve learning history
        **Validates: Requirements 5.1, 5.2**
        """
        # Create test user, domain, and term first
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Create user
                cursor.execute("""
                    INSERT INTO users (email, password_hash, first_name, last_name)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (test_email, 'test_hash', 'Test', 'User'))
                
                user_id = cursor.fetchone()['id']
                
                # Create domain node
                domain_data = {'name': 'Test Domain', 'description': 'Test Description'}
                cursor.execute("""
                    INSERT INTO tree_nodes (user_id, node_type, data)
                    VALUES (%s, %s, %s) RETURNING id
                """, (user_id, 'domain', json.dumps(domain_data)))
                
                domain_id = cursor.fetchone()['id']
                
                # Create term node
                term_data = {'term': 'Test Term', 'definition': 'Test Definition'}
                cursor.execute("""
                    INSERT INTO tree_nodes (parent_id, user_id, node_type, data)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (domain_id, user_id, 'term', json.dumps(term_data)))
                
                term_id = cursor.fetchone()['id']
                
                # Insert progress record
                cursor.execute("""
                    INSERT INTO progress_records 
                    (user_id, term_id, student_answer, correct_answer, is_correct, 
                     similarity_score, attempt_number, feedback)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, term_id, student_answer, correct_answer, 
                             is_correct, similarity_score, attempt_number, feedback
                """, (
                    user_id, term_id, progress_data_dict['student_answer'],
                    progress_data_dict['correct_answer'], progress_data_dict['is_correct'],
                    progress_data_dict['similarity_score'], progress_data_dict['attempt_number'],
                    progress_data_dict['feedback']
                ))
                
                inserted_record = dict(cursor.fetchone())
                record_id = inserted_record['id']
                
                # Retrieve progress record
                cursor.execute("""
                    SELECT id, user_id, term_id, student_answer, correct_answer, 
                           is_correct, similarity_score, attempt_number, feedback
                    FROM progress_records WHERE id = %s
                """, (record_id,))
                
                retrieved_record = dict(cursor.fetchone())
                
                # Verify round trip integrity
                assert retrieved_record['user_id'] == user_id
                assert retrieved_record['term_id'] == term_id
                assert retrieved_record['student_answer'] == progress_data_dict['student_answer']
                assert retrieved_record['correct_answer'] == progress_data_dict['correct_answer']
                assert retrieved_record['is_correct'] == progress_data_dict['is_correct']
                assert abs(float(retrieved_record['similarity_score']) - progress_data_dict['similarity_score']) < 0.01
                assert retrieved_record['attempt_number'] == progress_data_dict['attempt_number']
                assert retrieved_record['feedback'] == progress_data_dict['feedback']
                
                conn.commit()


if __name__ == "__main__":
    # Run tests locally
    pytest.main([__file__, "-v", "--tb=short"])