"""
Property-based tests for domain management service
Feature: tutor-system
"""
import pytest
import json
import uuid
from hypothesis import given, strategies as st, settings, HealthCheck
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.domain_management.handler import lambda_handler
from shared.database import get_db_connection
import psycopg2


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
def domain_with_terms(draw):
    """Generate a domain with terms"""
    domain_name = draw(valid_domain_name())
    domain_description = draw(valid_domain_description())
    
    # Generate 1-5 terms for the domain
    num_terms = draw(st.integers(min_value=1, max_value=5))
    terms = []
    used_terms = set()  # Track used term names to ensure uniqueness
    
    for _ in range(num_terms):
        # Generate unique term names
        term = draw(valid_term())
        # Ensure term name is unique within this domain
        while term in used_terms:
            term = draw(valid_term())
        used_terms.add(term)
        
        definition = draw(valid_definition())
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
    import time
    
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
                
                # Create a mock token for testing (not a real JWT)
                mock_token = f"test_token_{unique_id}"
                
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


@given(domain_data=domain_with_terms())
@settings(max_examples=100, deadline=60000, suppress_health_check=[HealthCheck.function_scoped_fixture])  # 60 second timeout per test
@pytest.mark.localstack
def test_domain_creation_and_retrieval_consistency(domain_data, test_environment, clean_database):
    """
    Property 2: Domain Creation and Retrieval Consistency
    For any student and valid knowledge domain, creating the domain should result in 
    it appearing in the student's domain list with all original terms and definitions intact.
    **Validates: Requirements 2.2, 2.3, 2.5**
    """
    token, user_id, email = create_test_user()
    
    try:
        # Step 1: Create domain
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
                        'email': email
                    }
                }
            }
        }
        
        create_response = lambda_handler(create_domain_event, {})
        
        # Verify domain creation succeeded
        assert create_response['statusCode'] == 201
        create_body = json.loads(create_response['body'])
        assert create_body['success'] is True
        assert 'data' in create_body
        
        domain_id = create_body['data']['id']
        created_domain = create_body['data']
        
        # Verify created domain has correct properties
        assert created_domain['name'] == domain_data['name']
        assert created_domain['description'] == domain_data['description']
        assert created_domain['term_count'] == 0
        assert created_domain['user_id'] == user_id
        
        # Step 2: Add terms to domain
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
                        'email': email
                    }
                }
            }
        }
        
        add_terms_response = lambda_handler(add_terms_event, {})
        
        # Verify terms were added successfully
        assert add_terms_response['statusCode'] == 201
        terms_body = json.loads(add_terms_response['body'])
        assert terms_body['success'] is True
        assert terms_body['data']['count'] == len(domain_data['terms'])
        
        created_terms = terms_body['data']['terms']
        
        # Step 3: Retrieve domain list
        get_domains_event = {
            'httpMethod': 'GET',
            'path': '/domains',
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email
                    }
                }
            }
        }
        
        get_domains_response = lambda_handler(get_domains_event, {})
        
        # Verify domain appears in list
        assert get_domains_response['statusCode'] == 200
        domains_body = json.loads(get_domains_response['body'])
        assert domains_body['success'] is True
        
        domains_list = domains_body['data']
        assert len(domains_list) == 1
        
        retrieved_domain = domains_list[0]
        
        # Step 4: Verify domain consistency
        assert retrieved_domain['id'] == domain_id
        assert retrieved_domain['name'] == domain_data['name']
        assert retrieved_domain['description'] == domain_data['description']
        assert retrieved_domain['term_count'] == len(domain_data['terms'])
        
        # Step 5: Retrieve terms for the domain
        get_terms_event = {
            'httpMethod': 'GET',
            'path': f'/domains/{domain_id}/terms',
            'pathParameters': {
                'domain_id': domain_id
            },
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id,
                        'email': email
                    }
                }
            }
        }
        
        get_terms_response = lambda_handler(get_terms_event, {})
        
        # Verify terms retrieval succeeded
        assert get_terms_response['statusCode'] == 200
        terms_list_body = json.loads(get_terms_response['body'])
        assert terms_list_body['success'] is True
        
        retrieved_terms = terms_list_body['data']
        
        # Step 6: Verify all terms and definitions are intact
        assert len(retrieved_terms) == len(domain_data['terms'])
        
        # Create maps for comparison (order might differ)
        original_terms_map = {term['term']: term['definition'] for term in domain_data['terms']}
        retrieved_terms_map = {term['term']: term['definition'] for term in retrieved_terms}
        
        # Property verification: All original terms and definitions should be intact
        assert len(original_terms_map) == len(retrieved_terms_map)
        
        for term_name, definition in original_terms_map.items():
            assert term_name in retrieved_terms_map
            assert retrieved_terms_map[term_name] == definition
        
        # Verify each retrieved term has the expected structure
        for term in retrieved_terms:
            assert 'id' in term
            assert 'term' in term
            assert 'definition' in term
            assert 'created_at' in term
            assert 'updated_at' in term
            assert term['term'] in original_terms_map
            assert term['definition'] == original_terms_map[term['term']]
        
        # Property verification: Domain creation and retrieval consistency
        # The domain should appear in the user's domain list with all original data intact
        # All terms and definitions should be preserved exactly as created
        
    finally:
        # Cleanup: Remove test user and associated data
        cleanup_test_user(email)


@pytest.mark.localstack
def test_domain_creation_consistency_with_duplicate_names(test_environment, clean_database):
    """
    Test that domain creation prevents duplicates within user scope
    """
    token, user_id, email = create_test_user()
    
    try:
        domain_data = {
            'name': 'Test Domain',
            'description': 'This is a test domain for duplicate testing'
        }
        
        # Create first domain
        create_event = {
            'httpMethod': 'POST',
            'path': '/domains',
            'body': json.dumps(domain_data),
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
        
        first_response = lambda_handler(create_event, {})
        assert first_response['statusCode'] == 201
        
        # Try to create duplicate domain
        second_response = lambda_handler(create_event, {})
        assert second_response['statusCode'] == 409  # Conflict
        
        # Verify only one domain exists
        get_domains_event = {
            'httpMethod': 'GET',
            'path': '/domains',
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
        
        get_response = lambda_handler(get_domains_event, {})
        assert get_response['statusCode'] == 200
        
        body = json.loads(get_response['body'])
        assert len(body['data']) == 1
        
    finally:
        cleanup_test_user(email)


@pytest.mark.localstack
def test_domain_retrieval_user_isolation(test_environment, clean_database):
    """
    Test that users can only retrieve their own domains
    """
    # Create two test users
    token1, user_id1, email1 = create_test_user()
    token2, user_id2, email2 = create_test_user()
    
    try:
        # User 1 creates a domain
        domain_data = {
            'name': 'User 1 Domain',
            'description': 'This domain belongs to user 1'
        }
        
        create_event = {
            'httpMethod': 'POST',
            'path': '/domains',
            'body': json.dumps(domain_data),
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id1,
                        'email': email1,
                        'cognito:username': email1,
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        create_response = lambda_handler(create_event, {})
        assert create_response['statusCode'] == 201
        
        # User 2 retrieves domains (should be empty)
        get_domains_event = {
            'httpMethod': 'GET',
            'path': '/domains',
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id2,
                        'email': email2,
                        'cognito:username': email2,
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        get_response = lambda_handler(get_domains_event, {})
        assert get_response['statusCode'] == 200
        
        body = json.loads(get_response['body'])
        assert len(body['data']) == 0  # User 2 should see no domains
        
        # User 1 retrieves domains (should see their domain)
        get_domains_event_user1 = {
            'httpMethod': 'GET',
            'path': '/domains',
            'headers': {},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': user_id1,
                        'email': email1,
                        'cognito:username': email1,
                        'email_verified': 'true'
                    }
                }
            }
        }
        
        get_response_user1 = lambda_handler(get_domains_event_user1, {})
        assert get_response_user1['statusCode'] == 200
        
        body_user1 = json.loads(get_response_user1['body'])
        assert len(body_user1['data']) == 1  # User 1 should see their domain
        assert body_user1['data'][0]['name'] == domain_data['name']
        
    finally:
        cleanup_test_user(email1)
        cleanup_test_user(email2)


@st.composite
def domain_with_structure(draw, num_terms=None):
    """Generate a domain with specific structural properties"""
    if num_terms is None:
        num_terms = draw(st.integers(min_value=1, max_value=5))
    
    # Generate unique domain name with timestamp to avoid conflicts
    import time
    unique_suffix = str(int(time.time() * 1000000))[-6:]  # Last 6 digits of microseconds
    base_name = draw(valid_domain_name())
    domain_name = f"{base_name}_{unique_suffix}"
    
    domain_description = draw(valid_domain_description())
    
    terms = []
    used_terms = set()  # Track used term names to ensure uniqueness within domain
    
    for _ in range(num_terms):
        # Generate unique term names
        term = draw(valid_term())
        # Ensure term name is unique within this domain
        while term in used_terms:
            term = draw(valid_term())
        used_terms.add(term)
        
        definition = draw(valid_definition())
        terms.append({
            'term': term,
            'definition': definition
        })
    
    return {
        'name': domain_name,
        'description': domain_description,
        'terms': terms,
        'structure': {
            'term_count': num_terms,
            'hierarchy_depth': 1  # All terms are direct children of domain
        }
    }


@given(
    domain1_data=domain_with_structure(),
    domain2_data=domain_with_structure()
)
@settings(max_examples=50, deadline=120000, suppress_health_check=[HealthCheck.function_scoped_fixture])  # 2 minute timeout per test
@pytest.mark.localstack
def test_domain_agnostic_processing_consistency(domain1_data, domain2_data, test_environment, clean_database, ensure_localstack_running):
    """
    Property 6: Domain-Agnostic Processing Consistency
    For any two knowledge domains with the same structural properties (number of terms, 
    hierarchy depth), the system should process them using identical operations 
    regardless of subject matter content.
    **Validates: Requirements 6.1, 6.3**
    """
    # Ensure both domains have the same structural properties
    if len(domain1_data['terms']) != len(domain2_data['terms']):
        # Skip this test case if structures don't match
        return
    
    # Ensure LocalStack is ready and secrets are available
    if not ensure_localstack_running:
        pytest.skip("LocalStack is not available")
    
    token, user_id, email = create_test_user()
    
    try:
        # Process both domains with identical operations
        domain_ids = []
        created_domains = []
        
        for i, domain_data in enumerate([domain1_data, domain2_data]):
            # Step 1: Create domain
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
            
            create_response = lambda_handler(create_domain_event, {})
            
            # Verify domain creation succeeded with identical response structure
            assert create_response['statusCode'] == 201
            create_body = json.loads(create_response['body'])
            assert create_body['success'] is True
            assert 'data' in create_body
            
            domain_id = create_body['data']['id']
            domain_ids.append(domain_id)
            created_domains.append(create_body['data'])
            
            # Verify identical response structure regardless of content
            expected_keys = {'id', 'name', 'description', 'term_count', 'user_id'}
            assert set(create_body['data'].keys()) == expected_keys
            
            # Step 2: Add terms with identical operations
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
            
            add_terms_response = lambda_handler(add_terms_event, {})
            
            # Verify identical response structure for term addition
            assert add_terms_response['statusCode'] == 201
            terms_body = json.loads(add_terms_response['body'])
            assert terms_body['success'] is True
            assert 'data' in terms_body
            assert 'terms' in terms_body['data']
            assert 'count' in terms_body['data']
            assert terms_body['data']['count'] == len(domain_data['terms'])
            
            # Verify each term has identical structure
            for term in terms_body['data']['terms']:
                expected_term_keys = {'id', 'term', 'definition'}
                assert set(term.keys()) == expected_term_keys
        
        # Step 3: Ensure database consistency before retrieval
        import time
        time.sleep(0.1)  # Brief pause to ensure database consistency
        
        # Force database connection refresh to ensure we see committed changes
        from shared.database import get_db_connection
        try:
            with get_db_connection() as conn:
                conn.commit()  # Ensure any pending transactions are committed
        except Exception:
            pass  # Ignore connection errors, continue with test
        
        # Step 3: Retrieve domains with identical operations (with retry for consistency)
        get_domains_event = {
            'httpMethod': 'GET',
            'path': '/domains',
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
        
        # Retry mechanism for domain retrieval to handle timing issues
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            get_domains_response = lambda_handler(get_domains_event, {})
            
            # Verify identical response structure for domain retrieval
            assert get_domains_response['statusCode'] == 200
            domains_body = json.loads(get_domains_response['body'])
            assert domains_body['success'] is True
            assert len(domains_body['data']) == 2
            
            # Check if term counts are correct, retry if not
            retrieved_domains = domains_body['data']
            retrieved_domains.sort(key=lambda d: d['created_at'])
            
            term_counts_correct = True
            for i, domain in enumerate(retrieved_domains):
                expected_count = len([domain1_data, domain2_data][i]['terms'])
                if domain['term_count'] != expected_count:
                    term_counts_correct = False
                    break
            
            if term_counts_correct or attempt == max_retries - 1:
                break
            
            # Wait before retry
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        
        # Step 4: Retrieve terms for both domains with identical operations
        retrieved_terms_list = []
        
        for domain_id in domain_ids:
            get_terms_event = {
                'httpMethod': 'GET',
                'path': f'/domains/{domain_id}/terms',
                'pathParameters': {
                    'domain_id': domain_id
                },
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
            
            get_terms_response = lambda_handler(get_terms_event, {})
            
            # Verify identical response structure for term retrieval
            assert get_terms_response['statusCode'] == 200
            terms_list_body = json.loads(get_terms_response['body'])
            assert terms_list_body['success'] is True
            
            retrieved_terms = terms_list_body['data']
            retrieved_terms_list.append(retrieved_terms)
            
            # Verify each term has identical structure
            for term in retrieved_terms:
                expected_term_keys = {'id', 'term', 'definition', 'created_at', 'updated_at'}
                assert set(term.keys()) == expected_term_keys
        
        # Property verification: Domain-agnostic processing consistency
        # Both domains should have been processed with identical operations
        # Response structures should be identical regardless of content
        
        # Verify structural consistency
        assert len(retrieved_terms_list[0]) == len(retrieved_terms_list[1])
        assert len(retrieved_terms_list[0]) == len(domain1_data['terms'])
        assert len(retrieved_terms_list[1]) == len(domain2_data['terms'])
        
        # Verify that the system processed both domains using the same operations
        # (evidenced by identical response structures and successful operations)
        # Check the domains retrieved after all operations are complete
        retrieved_domains = domains_body['data']
        
        # Sort domains by creation order to match with original data
        retrieved_domains.sort(key=lambda d: d['created_at'])
        original_domains = [domain1_data, domain2_data]
        
        for i, domain in enumerate(retrieved_domains):
            expected_term_count = len(original_domains[i]['terms'])
            actual_term_count = domain['term_count']
            
            # Add detailed error message for debugging
            if actual_term_count != expected_term_count:
                # Get actual terms from database for debugging
                debug_terms_event = {
                    'httpMethod': 'GET',
                    'path': f'/domains/{domain["id"]}/terms',
                    'pathParameters': {
                        'domain_id': domain['id']
                    },
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
                debug_response = lambda_handler(debug_terms_event, {})
                debug_terms = json.loads(debug_response['body'])['data'] if debug_response['statusCode'] == 200 else []
                
                raise AssertionError(
                    f"Domain term count mismatch for domain {i+1} ('{domain['name']}'). "
                    f"Expected {expected_term_count} term(s) but got {actual_term_count} terms in domain retrieval. "
                    f"Domain metadata: {domain}. "
                    f"Actual terms in database: {len(debug_terms)} terms. "
                    f"Original terms: {original_domains[i]['terms']}"
                )
            
            assert domain['user_id'] == user_id
        
        # Verify that retrieval operations work identically for both domains
        for terms_list in retrieved_terms_list:
            for term in terms_list:
                # Each term should have the same structure and data types
                assert isinstance(term['id'], str)
                assert isinstance(term['term'], str)
                assert isinstance(term['definition'], str)
                assert isinstance(term['created_at'], str)
                assert isinstance(term['updated_at'], str)
        
        # Property verification: The system processes domains with identical structural
        # properties using the same operations, regardless of subject matter content
        
    finally:
        # Cleanup: Remove test user and associated data
        cleanup_test_user(email)


@pytest.mark.localstack
def test_domain_agnostic_processing_with_different_subjects(test_environment, clean_database):
    """
    Test that domains from different subjects (AWS, Python, etc.) are processed identically
    """
    token, user_id, email = create_test_user()
    
    try:
        # Create domains with different subject matter but same structure
        aws_domain = {
            'name': 'AWS Certification',
            'description': 'Amazon Web Services certification terms and concepts',
            'terms': [
                {'term': 'EC2', 'definition': 'Elastic Compute Cloud - virtual servers in AWS'},
                {'term': 'S3', 'definition': 'Simple Storage Service - object storage service'}
            ]
        }
        
        python_domain = {
            'name': 'Python Programming',
            'description': 'Python programming language concepts and terminology',
            'terms': [
                {'term': 'List', 'definition': 'Ordered collection of items in Python'},
                {'term': 'Dict', 'definition': 'Key-value mapping data structure in Python'}
            ]
        }
        
        domains_data = [aws_domain, python_domain]
        domain_ids = []
        
        # Process both domains with identical operations
        for domain_data in domains_data:
            # Create domain
            create_event = {
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
            
            create_response = lambda_handler(create_event, {})
            assert create_response['statusCode'] == 201
            
            domain_id = json.loads(create_response['body'])['data']['id']
            domain_ids.append(domain_id)
            
            # Add terms
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
            
            add_terms_response = lambda_handler(add_terms_event, {})
            assert add_terms_response['statusCode'] == 201
        
        # Verify both domains are processed identically
        get_domains_event = {
            'httpMethod': 'GET',
            'path': '/domains',
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
        
        get_response = lambda_handler(get_domains_event, {})
        assert get_response['statusCode'] == 200
        
        body = json.loads(get_response['body'])
        assert len(body['data']) == 2
        
        # Both domains should have identical structure
        for domain in body['data']:
            assert domain['term_count'] == 2
            assert 'id' in domain
            assert 'name' in domain
            assert 'description' in domain
            assert 'created_at' in domain
            assert 'updated_at' in domain
        
        # Verify terms are processed identically
        for domain_id in domain_ids:
            get_terms_event = {
                'httpMethod': 'GET',
                'path': f'/domains/{domain_id}/terms',
                'pathParameters': {
                    'domain_id': domain_id
                },
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
            
            get_terms_response = lambda_handler(get_terms_event, {})
            assert get_terms_response['statusCode'] == 200
            
            terms_body = json.loads(get_terms_response['body'])
            assert len(terms_body['data']) == 2
            
            # Each term should have identical structure
            for term in terms_body['data']:
                assert 'id' in term
                assert 'term' in term
                assert 'definition' in term
                assert 'created_at' in term
                assert 'updated_at' in term
        
    finally:
        cleanup_test_user(email)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])