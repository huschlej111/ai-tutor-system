"""
Property-based tests for batch upload service
Feature: tutor-system, Property 9: Batch Upload Data Integrity
"""
import pytest
import json
import uuid
from hypothesis import given, strategies as st, settings, HealthCheck
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.batch_upload.handler import lambda_handler
from shared.database import get_db_connection
import psycopg2


# Safe character set excluding null characters and control characters
SAFE_CHARS = st.characters(
    min_codepoint=33,  # Start from exclamation mark (skip space)
    max_codepoint=126,  # End at tilde character
    blacklist_characters='\x00'  # Explicitly exclude null character
)

# Safe characters including space for internal use (not at start/end)
SAFE_CHARS_WITH_SPACE = st.characters(
    min_codepoint=32,  # Include space character
    max_codepoint=126,  # End at tilde character
    blacklist_characters='\x00'  # Explicitly exclude null character
)

# Test data generators
@st.composite
def valid_batch_metadata(draw):
    """Generate valid batch metadata"""
    return {
        'filename': draw(st.text(alphabet=SAFE_CHARS, min_size=5, max_size=50)),
        'version': '1.0',
        'created_date': '2025-01-01',
        'total_domains': draw(st.integers(min_value=1, max_value=5)),
        'total_terms': draw(st.integers(min_value=1, max_value=20))
    }


@st.composite
def valid_domain_name(draw):
    """Generate valid domain names without leading/trailing whitespace"""
    # Use alphanumeric and underscore characters only for domain names
    domain_chars = st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),  # Letters and digits
        min_codepoint=33, max_codepoint=126,  # Skip space at start/end
        blacklist_characters='\x00'
    ) | st.just('_')  # Add underscore
    
    # Generate core name without spaces at edges
    core_name = draw(st.text(alphabet=domain_chars, min_size=2, max_size=98))
    
    # Optionally add spaces in the middle
    if len(core_name) < 90 and draw(st.booleans()):
        # Insert a space somewhere in the middle (not at start/end)
        if len(core_name) > 2:
            insert_pos = draw(st.integers(min_value=1, max_value=len(core_name)-1))
            core_name = core_name[:insert_pos] + ' ' + core_name[insert_pos:]
    
    return core_name


@st.composite
def valid_domain_description(draw):
    """Generate valid domain descriptions without leading/trailing whitespace"""
    # Generate text that doesn't start or end with whitespace
    # Ensure we have enough words to meet the 10 character minimum
    words = draw(st.lists(
        st.text(alphabet=SAFE_CHARS, min_size=2, max_size=20),  # Longer words
        min_size=5, max_size=25  # More words to ensure length
    ))
    description = ' '.join(words)
    
    # Ensure minimum length of 10 characters
    while len(description) < 10:
        extra_word = draw(st.text(alphabet=SAFE_CHARS, min_size=3, max_size=10))
        description += ' ' + extra_word
    
    return description[:500]  # Limit to max length


@st.composite
def valid_term_name(draw):
    """Generate valid term names without leading/trailing whitespace"""
    # Use alphanumeric, hyphen, and underscore for term names
    term_chars = st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),  # Letters and digits
        min_codepoint=33, max_codepoint=126,  # Skip space at start/end
        blacklist_characters='\x00'
    ) | st.just('_') | st.just('-')
    
    # Generate core name without spaces at edges
    core_name = draw(st.text(alphabet=term_chars, min_size=2, max_size=198))
    
    # Optionally add spaces in the middle
    if len(core_name) < 190 and draw(st.booleans()):
        # Insert a space somewhere in the middle (not at start/end)
        if len(core_name) > 2:
            insert_pos = draw(st.integers(min_value=1, max_value=len(core_name)-1))
            core_name = core_name[:insert_pos] + ' ' + core_name[insert_pos:]
    
    return core_name


@st.composite
def valid_definition(draw):
    """Generate valid definitions without leading/trailing whitespace"""
    # Generate text that doesn't start or end with whitespace
    # Ensure we have enough words to meet the 10 character minimum
    words = draw(st.lists(
        st.text(alphabet=SAFE_CHARS, min_size=2, max_size=30),  # Longer words
        min_size=5, max_size=50  # More words to ensure length
    ))
    definition = ' '.join(words)
    
    # Ensure minimum length of 10 characters
    while len(definition) < 10:
        extra_word = draw(st.text(alphabet=SAFE_CHARS, min_size=3, max_size=15))
        definition += ' ' + extra_word
    
    return definition[:1000]  # Limit to max length


@st.composite
def batch_upload_term(draw):
    """Generate a valid batch upload term"""
    # Use safe characters for all text fields (no leading/trailing spaces)
    safe_text_short = st.text(alphabet=SAFE_CHARS, min_size=3, max_size=20)
    safe_text_medium = st.text(alphabet=SAFE_CHARS, min_size=2, max_size=15)
    safe_text_long = st.text(alphabet=SAFE_CHARS, min_size=3, max_size=20)
    
    return {
        'node_type': 'term',
        'data': {
            'term': draw(valid_term_name()),
            'definition': draw(valid_definition()),
            'difficulty': draw(st.sampled_from(['beginner', 'intermediate', 'advanced'])),
            'module': draw(safe_text_short)
        },
        'metadata': {
            'keywords': draw(st.lists(safe_text_medium, min_size=1, max_size=5)),
            'related_concepts': draw(st.lists(safe_text_long, min_size=0, max_size=3))
        }
    }


@st.composite
def batch_upload_domain(draw):
    """Generate a valid batch upload domain with terms"""
    # Generate unique domain name with timestamp to avoid conflicts
    import time
    unique_suffix = str(int(time.time() * 1000000))[-6:]  # Last 6 digits of microseconds
    base_name = draw(valid_domain_name())
    domain_name = f"{base_name}_{unique_suffix}"
    
    # Generate 1-5 terms for the domain
    num_terms = draw(st.integers(min_value=1, max_value=5))
    terms = []
    used_terms = set()  # Track used term names to ensure uniqueness (case-insensitive)
    
    for _ in range(num_terms):
        # Generate unique term names within this domain (case-insensitive)
        term_data = draw(batch_upload_term())
        term_name = term_data['data']['term']
        term_name_lower = term_name.lower()
        
        # Ensure term name is unique within this domain (case-insensitive)
        while term_name_lower in used_terms:
            term_data = draw(batch_upload_term())
            term_name = term_data['data']['term']
            term_name_lower = term_name.lower()
        
        used_terms.add(term_name_lower)
        terms.append(term_data)
    
    # Use safe characters for prerequisites and tags (no leading/trailing spaces)
    safe_prereq = st.text(alphabet=SAFE_CHARS, min_size=5, max_size=30)
    safe_tag = st.text(alphabet=SAFE_CHARS, min_size=3, max_size=15)
    
    return {
        'node_type': 'domain',
        'data': {
            'name': domain_name,
            'description': draw(valid_domain_description()),
            'subject': draw(st.sampled_from(['python', 'aws', 'javascript', 'general'])),
            'difficulty': draw(st.sampled_from(['beginner', 'intermediate', 'advanced'])),
            'estimated_hours': draw(st.integers(min_value=1, max_value=40)),
            'prerequisites': draw(st.lists(safe_prereq, min_size=0, max_size=3))
        },
        'metadata': {
            'version': 1,
            'tags': draw(st.lists(safe_tag, min_size=1, max_size=5))
        },
        'terms': terms
    }


@st.composite
def valid_batch_upload_data(draw):
    """Generate a complete valid batch upload data structure"""
    # Generate 1-3 domains
    num_domains = draw(st.integers(min_value=1, max_value=3))
    domains = []
    used_domain_names = set()  # Track used domain names to ensure uniqueness (case-insensitive)
    
    total_terms = 0
    for _ in range(num_domains):
        # Generate unique domain names across the batch (case-insensitive)
        domain_data = draw(batch_upload_domain())
        domain_name = domain_data['data']['name']
        domain_name_lower = domain_name.lower()
        
        # Ensure domain name is unique within this batch (case-insensitive)
        while domain_name_lower in used_domain_names:
            domain_data = draw(batch_upload_domain())
            domain_name = domain_data['data']['name']
            domain_name_lower = domain_name.lower()
        
        used_domain_names.add(domain_name_lower)
        domains.append(domain_data)
        total_terms += len(domain_data['terms'])
    
    # Generate metadata that matches the actual content
    safe_filename = st.text(alphabet=SAFE_CHARS, min_size=5, max_size=50)
    
    metadata = {
        'filename': draw(safe_filename),
        'version': '1.0',
        'created_date': '2025-01-01',
        'total_domains': num_domains,
        'total_terms': total_terms
    }
    
    return {
        'batch_metadata': metadata,
        'domains': domains
    }


def create_test_user():
    """Create a test user directly in the database and return user info"""
    import time
    
    unique_id = str(uuid.uuid4())[:8]
    user_id = str(uuid.uuid4())
    email = f'test_batch_{unique_id}@example.com'
    
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
                """, (user_id, email, 'dummy_hash_for_testing', 'Test', 'BatchUser'))
                
                result = cursor.fetchone()
                if result:
                    user_id = result[0]
                
                cursor.close()
                conn.commit()
                
                # Create a mock token for testing (not a real JWT)
                mock_token = f"test_batch_token_{unique_id}"
                
                return mock_token, user_id, email
                
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


def get_user_domains_and_terms(user_id: str):
    """Retrieve all domains and terms for a user from the database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all domains for the user
            cursor.execute("""
                SELECT id, data, metadata FROM tree_nodes 
                WHERE user_id = %s AND node_type = 'domain'
                ORDER BY created_at
            """, (user_id,))
            
            domains = cursor.fetchall()
            domain_data = []
            
            for domain in domains:
                domain_id, domain_json, domain_metadata = domain
                
                # Get terms for this domain
                cursor.execute("""
                    SELECT id, data, metadata FROM tree_nodes 
                    WHERE parent_id = %s AND node_type = 'term'
                    ORDER BY created_at
                """, (domain_id,))
                
                terms = cursor.fetchall()
                term_data = []
                
                for term in terms:
                    term_id, term_json, term_metadata = term
                    term_data.append({
                        'id': term_id,
                        'data': term_json,
                        'metadata': term_metadata or {}
                    })
                
                domain_data.append({
                    'id': domain_id,
                    'data': domain_json,
                    'metadata': domain_metadata or {},
                    'terms': term_data
                })
            
            cursor.close()
            return domain_data
            
    except Exception as e:
        print(f"Error retrieving user data: {e}")
        return []


@given(batch_data=valid_batch_upload_data())
@settings(max_examples=100, deadline=120000, suppress_health_check=[HealthCheck.function_scoped_fixture])  # 2 minute timeout per test
@pytest.mark.localstack
def test_batch_upload_data_integrity(batch_data, test_environment, clean_database):
    """
    Property 9: Batch Upload Data Integrity
    For any valid batch upload data, processing the batch should result in all domains 
    and terms being stored in the database with complete data preservation, maintaining 
    all original field values, metadata, and structural relationships.
    **Validates: Requirements 8.3, 8.4**
    """
    token, user_id, email = create_test_user()
    
    try:
        # Step 1: Validate the batch upload data
        validate_event = {
            'httpMethod': 'POST',
            'path': '/batch-upload/validate',
            'body': json.dumps({'batch_data': batch_data}),
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email,
                        'cognito:username': email,
                        'cognito:groups': 'instructor',  # Required for batch upload
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        validate_response = lambda_handler(validate_event, {})
        
        # Verify validation succeeded
        assert validate_response['statusCode'] == 200
        validate_body = json.loads(validate_response['body'])
        assert validate_body['success'] is True
        assert validate_body['data']['valid'] is True
        
        # Verify validation summary matches input data
        assert validate_body['data']['total_domains'] == len(batch_data['domains'])
        expected_total_terms = sum(len(domain['terms']) for domain in batch_data['domains'])
        assert validate_body['data']['total_terms'] == expected_total_terms
        
        # Step 2: Process the batch upload
        process_event = {
            'httpMethod': 'POST',
            'path': '/batch-upload/upload',
            'body': json.dumps({'batch_data': batch_data}),
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email,
                        'cognito:username': email,
                        'cognito:groups': 'instructor',  # Required for batch upload
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        process_response = lambda_handler(process_event, {})
        
        # Verify processing succeeded
        assert process_response['statusCode'] == 201
        process_body = json.loads(process_response['body'])
        assert process_body['success'] is True
        
        # Verify processing summary matches input data
        assert process_body['data']['domains_created'] == len(batch_data['domains'])
        assert process_body['data']['terms_created'] == expected_total_terms
        assert process_body['data']['domains_skipped'] == 0  # No duplicates in fresh test
        
        # Step 3: Retrieve all created data from database
        stored_data = get_user_domains_and_terms(user_id)
        
        # Verify correct number of domains and terms were stored
        assert len(stored_data) == len(batch_data['domains'])
        
        total_stored_terms = sum(len(domain['terms']) for domain in stored_data)
        assert total_stored_terms == expected_total_terms
        
        # Step 4: Verify data integrity - all original data preserved
        # Create maps for comparison (order might differ)
        original_domains_map = {domain['data']['name']: domain for domain in batch_data['domains']}
        stored_domains_map = {domain['data']['name']: domain for domain in stored_data}
        
        # Property verification: All domains should be preserved with complete data
        assert len(original_domains_map) == len(stored_domains_map)
        
        for domain_name, original_domain in original_domains_map.items():
            assert domain_name in stored_domains_map
            stored_domain = stored_domains_map[domain_name]
            
            # Verify domain data integrity
            original_data = original_domain['data']
            stored_data_json = stored_domain['data']
            
            # Check required fields are preserved
            assert stored_data_json['name'] == original_data['name']
            assert stored_data_json['description'] == original_data['description']
            
            # Check optional fields are preserved if present
            optional_domain_fields = ['subject', 'difficulty', 'estimated_hours', 'prerequisites']
            for field in optional_domain_fields:
                if field in original_data:
                    assert field in stored_data_json
                    assert stored_data_json[field] == original_data[field]
            
            # Verify domain metadata integrity
            if 'metadata' in original_domain:
                stored_metadata = stored_domain['metadata']
                original_metadata = original_domain['metadata']
                
                # Check that original metadata fields are preserved
                for key, value in original_metadata.items():
                    if key != 'term_count':  # term_count is managed by system
                        assert key in stored_metadata
                        assert stored_metadata[key] == value
            
            # Verify terms data integrity
            original_terms = original_domain['terms']
            stored_terms = stored_domain['terms']
            
            assert len(original_terms) == len(stored_terms)
            
            # Create maps for term comparison
            original_terms_map = {term['data']['term']: term for term in original_terms}
            stored_terms_map = {term['data']['term']: term for term in stored_terms}
            
            assert len(original_terms_map) == len(stored_terms_map)
            
            for term_name, original_term in original_terms_map.items():
                assert term_name in stored_terms_map
                stored_term = stored_terms_map[term_name]
                
                # Verify term data integrity
                original_term_data = original_term['data']
                stored_term_data = stored_term['data']
                
                # Check required fields are preserved
                assert stored_term_data['term'] == original_term_data['term']
                assert stored_term_data['definition'] == original_term_data['definition']
                
                # Check optional fields are preserved if present
                optional_term_fields = ['difficulty', 'module', 'examples', 'code_example']
                for field in optional_term_fields:
                    if field in original_term_data:
                        assert field in stored_term_data
                        assert stored_term_data[field] == original_term_data[field]
                
                # Verify term metadata integrity
                if 'metadata' in original_term:
                    stored_term_metadata = stored_term['metadata']
                    original_term_metadata = original_term['metadata']
                    
                    # Check that original metadata fields are preserved
                    for key, value in original_term_metadata.items():
                        assert key in stored_term_metadata
                        assert stored_term_metadata[key] == value
        
        # Step 5: Verify upload history was recorded
        history_event = {
            'httpMethod': 'GET',
            'path': '/batch-upload/history',
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email,
                        'cognito:username': email,
                        'cognito:groups': 'instructor',  # Required for batch upload
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        history_response = lambda_handler(history_event, {})
        
        # Verify history retrieval succeeded
        assert history_response['statusCode'] == 200
        history_body = json.loads(history_response['body'])
        assert history_body['success'] is True
        
        upload_history = history_body['data']
        assert len(upload_history) >= 1
        
        # Find the upload record for this batch
        latest_upload = upload_history[0]  # Should be most recent
        assert latest_upload['filename'] == batch_data['batch_metadata']['filename']
        assert latest_upload['subject_count'] == len(batch_data['domains'])
        assert latest_upload['status'] == 'completed'
        
        # Property verification: Batch Upload Data Integrity
        # All domains and terms from the batch upload should be stored in the database
        # with complete data preservation, maintaining all original field values,
        # metadata, and structural relationships.
        
    finally:
        # Cleanup: Remove test user and associated data
        cleanup_test_user(email)


@pytest.mark.localstack
def test_batch_upload_duplicate_handling(test_environment, clean_database):
    """
    Test that batch upload correctly handles duplicate domains
    """
    token, user_id, email = create_test_user()
    
    try:
        # Create initial batch data
        batch_data = {
            'batch_metadata': {
                'filename': 'test_duplicates.json',
                'version': '1.0',
                'created_date': '2025-01-01',
                'total_domains': 1,
                'total_terms': 2
            },
            'domains': [
                {
                    'node_type': 'domain',
                    'data': {
                        'name': 'Test Domain for Duplicates',
                        'description': 'This is a test domain for duplicate handling'
                    },
                    'metadata': {
                        'version': 1,
                        'tags': ['test']
                    },
                    'terms': [
                        {
                            'node_type': 'term',
                            'data': {
                                'term': 'Test Term 1',
                                'definition': 'This is the first test term definition'
                            },
                            'metadata': {
                                'keywords': ['test']
                            }
                        },
                        {
                            'node_type': 'term',
                            'data': {
                                'term': 'Test Term 2',
                                'definition': 'This is the second test term definition'
                            },
                            'metadata': {
                                'keywords': ['test']
                            }
                        }
                    ]
                }
            ]
        }
        
        # Process first batch
        process_event = {
            'httpMethod': 'POST',
            'path': '/batch-upload/upload',
            'body': json.dumps({'batch_data': batch_data}),
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email,
                        'cognito:username': email,
                        'cognito:groups': 'instructor',  # Required for batch upload
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        first_response = lambda_handler(process_event, {})
        assert first_response['statusCode'] == 201
        
        first_body = json.loads(first_response['body'])
        assert first_body['data']['domains_created'] == 1
        assert first_body['data']['terms_created'] == 2
        assert first_body['data']['domains_skipped'] == 0
        
        # Process same batch again (should skip duplicates)
        second_response = lambda_handler(process_event, {})
        assert second_response['statusCode'] == 201
        
        second_body = json.loads(second_response['body'])
        assert second_body['data']['domains_created'] == 0
        assert second_body['data']['terms_created'] == 0
        assert second_body['data']['domains_skipped'] == 1
        
        # Verify only one domain exists in database
        stored_data = get_user_domains_and_terms(user_id)
        assert len(stored_data) == 1
        assert len(stored_data[0]['terms']) == 2
        
    finally:
        cleanup_test_user(email)


@pytest.mark.localstack
def test_batch_upload_transaction_rollback(test_environment, clean_database):
    """
    Test that batch upload rolls back on validation failures
    """
    token, user_id, email = create_test_user()
    
    try:
        # Create batch data with invalid structure (missing required fields)
        invalid_batch_data = {
            'batch_metadata': {
                'filename': 'invalid_test.json',
                'version': '1.0',
                'created_date': '2025-01-01',
                'total_domains': 1,
                'total_terms': 1
            },
            'domains': [
                {
                    'node_type': 'domain',
                    'data': {
                        'name': 'Valid Domain Name',
                        # Missing required 'description' field
                    },
                    'terms': [
                        {
                            'node_type': 'term',
                            'data': {
                                'term': 'Valid Term',
                                'definition': 'Valid definition for the term'
                            }
                        }
                    ]
                }
            ]
        }
        
        # Attempt to process invalid batch
        process_event = {
            'httpMethod': 'POST',
            'path': '/batch-upload/upload',
            'body': json.dumps({'batch_data': invalid_batch_data}),
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email,
                        'cognito:username': email,
                        'cognito:groups': 'instructor',  # Required for batch upload
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        response = lambda_handler(process_event, {})
        
        # Should fail validation
        assert response['statusCode'] == 400
        
        # Verify no data was created in database
        stored_data = get_user_domains_and_terms(user_id)
        assert len(stored_data) == 0
        
    finally:
        cleanup_test_user(email)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])