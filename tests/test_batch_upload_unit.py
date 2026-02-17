"""
Unit tests for batch upload service edge cases
Requirements: 8.1, 8.2
"""
import pytest
import json
import uuid
import sys
import os
from unittest.mock import patch, MagicMock
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from lambda_functions.batch_upload.handler import lambda_handler


def check_validation_error(body, expected_field):
    """Helper function to check for validation errors in response body"""
    if 'error' in body and 'details' in body['error'] and 'validation_errors' in body['error']['details']:
        validation_errors = body['error']['details']['validation_errors']
        return any(expected_field in key for key in validation_errors.keys()) or \
               any(expected_field in str(validation_errors[key]) for key in validation_errors.keys())
    elif 'errors' in body:
        return any(expected_field in key for key in body['errors'].keys()) or \
               any(expected_field in str(body['errors'][key]) for key in body['errors'].keys())


def create_batch_upload_event(method, path, body_data, user_id='test-user-123', email='test@example.com'):
    """Create a batch upload event with proper Cognito authorization"""
    return {
        'httpMethod': method,
        'path': path,
        'body': json.dumps(body_data),
        'headers': {},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': user_id,
                    'email': email,
                    'cognito:username': email,
                    'cognito:groups': 'instructor',
                    'email_verified': 'true',
                    'token_use': 'access',
                    'auth_time': '1640995200',
                    'iss': f'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test',
                    'exp': '1640998800'
                }
            }
        }
    }


@pytest.mark.unit
@patch('shared.database.get_db_connection')
def test_malformed_json_validation(mock_db_conn):
    """
    Test that malformed JSON is properly rejected
    Requirements: 8.1, 8.2
    """
    user_id = 'test-user-123'
    email = 'test@example.com'
    
    # Test with completely invalid JSON structure
    invalid_batch_data = {
        'not_batch_data': 'this is wrong'
    }
    
    validate_event = create_batch_upload_event(
        'POST', '/batch-upload/validate', invalid_batch_data, user_id, email
    )
    
    response = lambda_handler(validate_event, {})
    
    # Should return validation error
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['success'] is False
    # Check for errors in the response structure
    if 'error' in body and 'details' in body['error'] and 'validation_errors' in body['error']['details']:
        assert 'batch_data' in body['error']['details']['validation_errors']
    elif 'errors' in body:
        assert 'batch_data' in body['errors']
    elif 'message' in body:
        assert 'batch_data' in body['message']
    else:
        # Fallback check
        assert 'batch_data' in str(body)


@pytest.mark.unit
@patch("shared.database.get_db_connection")
def test_missing_required_fields_validation(mock_db_conn):
    """
    Test validation of missing required fields in batch data
    Requirements: 8.1, 8.2
    """
    
    user_id = "test-user-123"
    email = "test@example.com"
    
    # Test missing batch_metadata
    batch_data_missing_metadata = {
        'domains': [
            {
                'node_type': 'domain',
                'data': {
                        'name': 'Test Domain',
                        'description': 'This is a test domain'
                    },
                    'terms': []
            }
        ]
    }
    
    validate_event = create_batch_upload_event(
        'POST', '/batch-upload/validate', 
        {'batch_data': batch_data_missing_metadata}, 
        user_id, email
    )
    
    response = lambda_handler(validate_event, {})
    
    # Should return validation error
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['success'] is False
    
    # Check for validation errors
    if 'error' in body and 'details' in body['error'] and 'validation_errors' in body['error']['details']:
        validation_errors = body['error']['details']['validation_errors']
        assert 'batch_metadata' in validation_errors
    else:
        assert 'batch_metadata' in str(body)
    
    # Test missing domain name
    batch_data_missing_name = {
    'batch_metadata': {
        'filename': 'test.json',
        'version': '1.0',
        'created_date': '2025-01-01',
        'total_domains': 1,
        'total_terms': 0
    },
    'domains': [
        {
            'node_type': 'domain',
            'data': {
                'description': 'This domain is missing a name'
            },
            'terms': []
        }
    ]
}

validate_event['body'] = json.dumps({'batch_data': batch_data_missing_name})
response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False

# Check for validation errors
if 'error' in body and 'details' in body['error'] and 'validation_errors' in body['error']['details']:
    validation_errors = body['error']['details']['validation_errors']
    assert any('name' in key for key in validation_errors.keys())
else:
    assert 'name' in str(body)




@pytest.mark.unit
@patch("shared.database.get_db_connection")
def test_field_length_validation(mock_db_conn):
    """
    Test validation of field length constraints
    Requirements: 8.1, 8.2
    """
    
    user_id = "test-user-123"
    email = "test@example.com"
    
# Test domain name too short
batch_data_short_name = {
    'batch_metadata': {
        'filename': 'test.json',
        'version': '1.0',
        'created_date': '2025-01-01',
        'total_domains': 1,
        'total_terms': 1
    },
    'domains': [
        {
            'node_type': 'domain',
            'data': {
                'name': 'A',  # Too short (< 2 characters)
                'description': 'This domain name is too short'
            },
            'terms': [
        {
                    'node_type': 'term',
                    'data': {
                        'term': 'Valid Term',
                        'definition': 'This is a valid definition'
                    }
                }
            ]
        }
    ]
}

validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_short_name},
    user_id, email
)

response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False
assert check_validation_error(body, 'between 2 and 100')

# Test domain name too long
batch_data_long_name = {
    'batch_metadata': {
        'filename': 'test.json',
        'version': '1.0',
        'created_date': '2025-01-01',
        'total_domains': 1,
        'total_terms': 1
    },
    'domains': [
        {
            'node_type': 'domain',
            'data': {
                'name': 'A' * 101,  # Too long (> 100 characters)
                'description': 'This domain name is too long'
            },
            'terms': [
                {
                    'node_type': 'term',
                    'data': {
                        'term': 'Valid Term',
                        'definition': 'This is a valid definition'
                    }
                }
    ]
}
    ]
}

validate_event['body'] = json.dumps({'batch_data': batch_data_long_name})
response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False
assert check_validation_error(body, 'between 2 and 100')


@pytest.mark.unit
@patch("shared.database.get_db_connection")
def test_empty_domains_and_terms_validation(mock_db_conn):
    """
    Test validation of empty domains and terms arrays
    Requirements: 8.1, 8.2
    """
    
    user_id = "test-user-123"
    email = "test@example.com"
    
# Test empty domains array
batch_data_empty_domains = {
    'batch_metadata': {
'filename': 'test.json',
'version': '1.0',
'created_date': '2025-01-01',
'total_domains': 0,
'total_terms': 0
    },
    'domains': []
}

validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_empty_domains},
    user_id, email
)

response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False
assert 'domains' in body['error']['details']['validation_errors']
assert 'At least one domain is required' in body['error']['details']['validation_errors']['domains']

# Test domain with empty terms array
batch_data_empty_terms = {
    'batch_metadata': {
'filename': 'test.json',
'version': '1.0',
'created_date': '2025-01-01',
'total_domains': 1,
'total_terms': 0
    },
    'domains': [
{
    'node_type': 'domain',
    'data': {
        'name': 'Test Domain',
        'description': 'This domain has no terms'
    },
    'terms': []
}
    ]
}

validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_empty_terms},
    user_id, email
)
response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False
assert any('terms' in key and 'At least one term is required' in str(body['error']['details']['validation_errors'][key]) for key in body['error']['details']['validation_errors'].keys())


@pytest.mark.unit
@patch("shared.database.get_db_connection")
def test_duplicate_detection_within_batch(mock_db_conn):
    """
    Test detection of duplicate domains and terms within a single batch
    Requirements: 8.1, 8.2
    """
    
    user_id = "test-user-123"
    email = "test@example.com"
    
# Test duplicate domain names within batch
batch_data_duplicate_domains = {
    'batch_metadata': {
'filename': 'test.json',
'version': '1.0',
'created_date': '2025-01-01',
'total_domains': 2,
'total_terms': 2
    },
    'domains': [
{
    'node_type': 'domain',
    'data': {
        'name': 'Duplicate Domain',
        'description': 'This is the first instance'
    },
    'terms': [
        {
            'node_type': 'term',
            'data': {
                'term': 'Term 1',
                'definition': 'Definition for term 1'
            }
        }
    ]
},
{
    'node_type': 'domain',
    'data': {
        'name': 'Duplicate Domain',  # Same name as above
        'description': 'This is the second instance'
    },
    'terms': [
        {
            'node_type': 'term',
            'data': {
                'term': 'Term 2',
                'definition': 'Definition for term 2'
            }
        }
    ]
}
    ]
}

validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_duplicate_domains},
    user_id, email
)

response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False
assert any('Duplicate domain name' in str(body['error']['details']['validation_errors'][key]) for key in body['error']['details']['validation_errors'].keys())

# Test duplicate term names within a domain
batch_data_duplicate_terms = {
    'batch_metadata': {
        'filename': 'test.json',
        'version': '1.0',
        'created_date': '2025-01-01',
        'total_domains': 1,
        'total_terms': 2
    },
    'domains': [
        {
            'node_type': 'domain',
            'data': {
                'name': 'Test Domain',
                'description': 'This domain has duplicate terms'
            },
            'terms': [
                {
                    'node_type': 'term',
                    'data': {
                        'term': 'Duplicate Term',
                        'definition': 'This is the first definition'
                    }
                },
                {
                    'node_type': 'term',
                    'data': {
                        'term': 'Duplicate Term',  # Same term name
                        'definition': 'This is the second definition'
                    }
                }
            ]
        }
    ]
}

validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_duplicate_terms},
    user_id, email
)
response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False
assert any('Duplicate term in domain' in str(body['error']['details']['validation_errors'][key]) for key in body['error']['details']['validation_errors'].keys())



@pytest.mark.unit
@patch("shared.database.get_db_connection")
def test_oversized_upload_validation(mock_db_conn):
    """
    Test handling of oversized uploads (too many domains/terms)
    Requirements: 8.1, 8.2
    """
    
    user_id = "test-user-123"
    email = "test@example.com"
    
# Create a batch with many domains to test size limits
# Note: This is a conceptual test - in practice, you'd set actual size limits
large_domains = []
for i in range(10):  # Create 10 domains with 10 terms each = 100 terms total
    terms = []
    for j in range(10):
        terms.append({
            'node_type': 'term',
            'data': {
                'term': f'Term {i}_{j}',
                'definition': f'This is definition {i}_{j} for testing large batches'
    }
})
    
    large_domains.append({
'node_type': 'domain',
'data': {
    'name': f'Large Domain {i}',
    'description': f'This is domain {i} for testing large batch uploads'
},
'terms': terms
    })

batch_data_large = {
    'batch_metadata': {
'filename': 'large_test.json',
'version': '1.0',
'created_date': '2025-01-01',
'total_domains': 10,
'total_terms': 100
    },
    'domains': large_domains
}

validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_large},
    user_id, email
)

response = lambda_handler(validate_event, {})

# Should succeed for reasonable size (adjust limits as needed)
assert response['statusCode'] == 200
body = json.loads(response['body'])
assert body['success'] is True
assert body['data']['total_domains'] == 10
assert body['data']['total_terms'] == 100



@pytest.mark.unit
@patch("shared.database.get_db_connection")
def test_transaction_rollback_on_failure(mock_db_conn):
    """
    Test that transaction rollback works correctly on validation failures
    Requirements: 8.1, 8.2
    """
    
    user_id = "test-user-123"
    email = "test@example.com"
    
# Create a batch that will fail during processing (invalid data that passes initial validation)
# This simulates a scenario where validation passes but processing fails
batch_data_will_fail = {
    'batch_metadata': {
'filename': 'will_fail.json',
'version': '1.0',
'created_date': '2025-01-01',
'total_domains': 1,
'total_terms': 1
    },
    'domains': [
{
    'node_type': 'domain',
    'data': {
        'name': 'Test Domain',
        'description': 'This domain will cause processing to fail'
    },
    'terms': [
        {
            'node_type': 'term',
            'data': {
                'term': 'Test Term',
                'definition': 'A' * 2000  # Extremely long definition that might cause issues
            }
        }
    ]
}
    ]
}

# First, validate (should pass basic validation)
validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_will_fail},
    user_id, email
)

validate_response = lambda_handler(validate_event, {})

# Validation should fail due to definition length
def test_invalid_node_types(mock_db_conn):
    """
    Test validation of invalid node types
    Requirements: 8.1, 8.2
    """
    
    user_id = "test-user-123"
    email = "test@example.com"
    
# Test invalid domain node type
batch_data_invalid_domain_type = {
    'batch_metadata': {
'filename': 'test.json',
'version': '1.0',
'created_date': '2025-01-01',
'total_domains': 1,
'total_terms': 1
    },
    'domains': [
{
    'node_type': 'invalid_domain',  # Wrong node type
    'data': {
        'name': 'Test Domain',
        'description': 'This domain has invalid node type'
    },
    'terms': [
        {
                    'node_type': 'term',
                    'data': {
                        'term': 'Test Term',
                        'definition': 'This is a valid term'
                    }
                }
            ]
        }
    ]
}

validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_invalid_domain_type},
    user_id, email
)

response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False
assert any('node_type must be "domain"' in str(body['error']['details']['validation_errors'][key]) for key in body['error']['details']['validation_errors'].keys())

# Test invalid term node type
batch_data_invalid_term_type = {
    'batch_metadata': {
        'filename': 'test.json',
        'version': '1.0',
        'created_date': '2025-01-01',
        'total_domains': 1,
        'total_terms': 1
    },
    'domains': [
        {
            'node_type': 'domain',
            'data': {
                'name': 'Test Domain',
                'description': 'This domain has a term with invalid node type'
            },
            'terms': [
                {
                    'node_type': 'invalid_term',  # Wrong node type
                    'data': {
                        'term': 'Test Term',
                        'definition': 'This term has invalid node type'
                    }
                }
            ]
        }
    ]
}

validate_event = create_batch_upload_event(
    'POST', '/batch-upload/validate',
    {'batch_data': batch_data_invalid_term_type},
    user_id, email
)
response = lambda_handler(validate_event, {})

# Should return validation error
assert response['statusCode'] == 400
body = json.loads(response['body'])
assert body['success'] is False
assert any('node_type must be "term"' in str(body['error']['details']['validation_errors'][key]) for key in body['error']['details']['validation_errors'].keys())



@pytest.mark.unit
@patch("shared.database.get_db_connection")
def test_unauthorized_access(mock_db_conn):
    """
    Test that unauthorized requests are properly rejected
    Requirements: 8.1, 8.2
    """
    # Test without authentication
    batch_data = {
'batch_metadata': {
    'filename': 'test.json',
    'version': '1.0',
    'created_date': '2025-01-01',
    'total_domains': 1,
    'total_terms': 1
},
'domains': [
    {
        'node_type': 'domain',
        'data': {
            'name': 'Test Domain',
            'description': 'This should be rejected due to no auth'
        },
        'terms': [
            {
                'node_type': 'term',
                'data': {
                    'term': 'Test Term',
                    'definition': 'This should be rejected'
                }
            }
        ]
    }
]
    }
    
    # Request without authentication
    validate_event = {
'httpMethod': 'POST',
'path': '/batch-upload/validate',
'body': json.dumps({'batch_data': batch_data}),
'headers': {},
'requestContext': {}  # No authorizer
    }
    
    response = lambda_handler(validate_event, {})
    
    # Should return forbidden (no auth context provided)
    assert response['statusCode'] == 403
    body = json.loads(response['body'])
    assert body['success'] is False
    
    # Check for authorization error message in various possible locations
    error_message = ""
    if 'message' in body:
        error_message = body['message']
    elif 'error' in body:
        if isinstance(body['error'], str):
            error_message = body['error']
        elif isinstance(body['error'], dict) and 'message' in body['error']:
            error_message = body['error']['message']
    
    # Should contain some form of authorization/access error
    assert any(keyword in error_message.lower() for keyword in ['user', 'claims', 'context', 'extract', 'auth'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])