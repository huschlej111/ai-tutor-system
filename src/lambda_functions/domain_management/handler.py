"""
Domain Management Lambda Function Handler
Handles CRUD operations for knowledge domains and terms
Requirements: 2.1, 2.2, 2.3, 2.4
"""
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from shared.database import get_db_cursor, execute_query, execute_query_one
from shared.response_utils import (
    create_success_response, create_created_response, create_error_response,
    create_validation_error_response, create_not_found_response,
    parse_request_body, get_path_parameters, get_query_parameters,
    handle_error
)
from shared.auth_utils import extract_user_from_cognito_event

logger = logging.getLogger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for domain management operations
    """
    try:
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        # Verify authentication for all domain operations using Cognito
        auth_result = extract_user_from_cognito_event(event)
        if not auth_result['valid']:
            return create_error_response(401, 'Unauthorized')
        
        user_id = auth_result['user_id']
        
        if http_method == 'POST':
            if path.endswith('/domains'):
                return handle_create_domain(event, user_id)
            elif '/domains/' in path and path.endswith('/terms'):
                return handle_add_terms(event, user_id)
        elif http_method == 'GET':
            if path.endswith('/domains'):
                return handle_get_domains(event, user_id)
            elif '/domains/' in path and not path.endswith('/terms'):
                return handle_get_domain(event, user_id)
            elif '/domains/' in path and path.endswith('/terms'):
                return handle_get_terms(event, user_id)
        elif http_method == 'PUT':
            if '/domains/' in path and not path.endswith('/terms'):
                return handle_update_domain(event, user_id)
            elif '/domains/' in path and '/terms/' in path:
                return handle_update_term(event, user_id)
        elif http_method == 'DELETE':
            if '/domains/' in path and not path.endswith('/terms'):
                return handle_delete_domain(event, user_id)
            elif '/domains/' in path and '/terms/' in path:
                return handle_delete_term(event, user_id)
        
        return create_error_response(404, 'Endpoint not found')
        
    except Exception as e:
        logger.error(f"Domain management error: {str(e)}")
        return handle_error(e)


def handle_create_domain(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Handle domain creation with tree_nodes table integration
    Requirements: 2.1, 2.2
    """
    try:
        body = parse_request_body(event)
        
        # Validate required fields
        validation_errors = {}
        if not body.get('name'):
            validation_errors['name'] = 'Domain name is required'
        if not body.get('description'):
            validation_errors['description'] = 'Domain description is required'
            
        if validation_errors:
            return create_validation_error_response(validation_errors)
        
        name = body['name'].strip()
        description = body['description'].strip()
        
        # Additional validation
        if len(name) < 2 or len(name) > 100:
            validation_errors['name'] = 'Domain name must be between 2 and 100 characters'
        if len(description) < 10 or len(description) > 500:
            validation_errors['description'] = 'Domain description must be between 10 and 500 characters'
            
        if validation_errors:
            return create_validation_error_response(validation_errors)
        
        # Check for duplicate domain names for this user
        existing_domain = execute_query_one(
            """
            SELECT id FROM tree_nodes 
            WHERE user_id = %s AND node_type = 'domain' 
            AND data->>'name' = %s
            """,
            (user_id, name)
        )
        
        if existing_domain:
            return create_error_response(409, 'Domain with this name already exists')
        
        # Create domain data structure
        domain_data = {
            'name': name,
            'description': description,
            'created_by': user_id
        }
        
        # Insert domain into tree_nodes table
        domain_id = str(uuid.uuid4())
        execute_query(
            """
            INSERT INTO tree_nodes (id, user_id, node_type, data, metadata)
            VALUES (%s, %s, 'domain', %s, %s)
            """,
            (domain_id, user_id, json.dumps(domain_data), json.dumps({'term_count': 0}))
        )
        
        # Return created domain
        domain = {
            'id': domain_id,
            'name': name,
            'description': description,
            'term_count': 0,
            'user_id': user_id
        }
        
        return create_created_response(domain, 'Domain created successfully')
        
    except Exception as e:
        logger.error(f"Error creating domain: {str(e)}")
        return handle_error(e)


def handle_get_domains(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Handle retrieving user domains with ownership filtering
    Requirements: 2.3, 2.5
    """
    try:
        # Get domains for the authenticated user
        domains = execute_query(
            """
            SELECT 
                tn.id,
                tn.data->>'name' as name,
                tn.data->>'description' as description,
                COALESCE(tn.metadata->>'term_count', '0') as term_count,
                tn.user_id,
                tn.created_at,
                tn.updated_at
            FROM tree_nodes tn
            WHERE tn.user_id = %s AND tn.node_type = 'domain'
            ORDER BY tn.created_at DESC
            """,
            (user_id,)
        )
        
        domain_list = []
        for domain in domains:
            domain_list.append({
                'id': domain[0],
                'name': domain[1],
                'description': domain[2],
                'term_count': int(domain[3]) if domain[3] else 0,
                'user_id': domain[4],
                'created_at': domain[5].isoformat() if domain[5] else None,
                'updated_at': domain[6].isoformat() if domain[6] else None
            })
        
        return create_success_response(domain_list)
        
    except Exception as e:
        logger.error(f"Error retrieving domains: {str(e)}")
        return handle_error(e)


def handle_get_domain(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle retrieving a specific domain"""
    try:
        path_params = get_path_parameters(event)
        domain_id = path_params.get('domain_id')
        
        if not domain_id:
            return create_error_response(400, 'Domain ID is required')
        
        # Get domain with ownership check
        domain = execute_query_one(
            """
            SELECT 
                tn.id,
                tn.data->>'name' as name,
                tn.data->>'description' as description,
                COALESCE(tn.metadata->>'term_count', '0') as term_count,
                tn.user_id,
                tn.created_at,
                tn.updated_at
            FROM tree_nodes tn
            WHERE tn.id = %s AND tn.user_id = %s AND tn.node_type = 'domain'
            """,
            (domain_id, user_id)
        )
        
        if not domain:
            return create_not_found_response('Domain not found')
        
        domain_data = {
            'id': domain[0],
            'name': domain[1],
            'description': domain[2],
            'term_count': int(domain[3]) if domain[3] else 0,
            'user_id': domain[4],
            'created_at': domain[5].isoformat() if domain[5] else None,
            'updated_at': domain[6].isoformat() if domain[6] else None
        }
        
        return create_success_response(domain_data)
        
    except Exception as e:
        logger.error(f"Error retrieving domain: {str(e)}")
        return handle_error(e)


def handle_update_domain(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle domain updates"""
    try:
        path_params = get_path_parameters(event)
        domain_id = path_params.get('domain_id')
        
        if not domain_id:
            return create_error_response(400, 'Domain ID is required')
        
        body = parse_request_body(event)
        
        # Check if domain exists and user owns it
        existing_domain = execute_query_one(
            """
            SELECT data FROM tree_nodes 
            WHERE id = %s AND user_id = %s AND node_type = 'domain'
            """,
            (domain_id, user_id)
        )
        
        if not existing_domain:
            return create_not_found_response('Domain not found')
        
        current_data = existing_domain[0]
        
        # Update fields if provided
        if 'name' in body:
            name = body['name'].strip()
            if len(name) < 2 or len(name) > 100:
                return create_validation_error_response({
                    'name': 'Domain name must be between 2 and 100 characters'
                })
            
            # Check for duplicate names (excluding current domain)
            duplicate = execute_query_one(
                """
                SELECT id FROM tree_nodes 
                WHERE user_id = %s AND node_type = 'domain' 
                AND data->>'name' = %s AND id != %s
                """,
                (user_id, name, domain_id)
            )
            
            if duplicate:
                return create_error_response(409, 'Domain with this name already exists')
            
            current_data['name'] = name
        
        if 'description' in body:
            description = body['description'].strip()
            if len(description) < 10 or len(description) > 500:
                return create_validation_error_response({
                    'description': 'Domain description must be between 10 and 500 characters'
                })
            current_data['description'] = description
        
        # Update domain
        execute_query(
            """
            UPDATE tree_nodes 
            SET data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            """,
            (json.dumps(current_data), domain_id, user_id)
        )
        
        return create_success_response({'id': domain_id}, 'Domain updated successfully')
        
    except Exception as e:
        logger.error(f"Error updating domain: {str(e)}")
        return handle_error(e)


def handle_delete_domain(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle domain deletion with cascade operations"""
    try:
        path_params = get_path_parameters(event)
        domain_id = path_params.get('domain_id')
        
        if not domain_id:
            return create_error_response(400, 'Domain ID is required')
        
        # Check if domain exists and user owns it
        existing_domain = execute_query_one(
            """
            SELECT id FROM tree_nodes 
            WHERE id = %s AND user_id = %s AND node_type = 'domain'
            """,
            (domain_id, user_id)
        )
        
        if not existing_domain:
            return create_not_found_response('Domain not found')
        
        # Delete domain (cascade will handle terms due to foreign key constraint)
        execute_query(
            "DELETE FROM tree_nodes WHERE id = %s AND user_id = %s",
            (domain_id, user_id)
        )
        
        return create_success_response({'id': domain_id}, 'Domain deleted successfully')
        
    except Exception as e:
        logger.error(f"Error deleting domain: {str(e)}")
        return handle_error(e)


def handle_add_terms(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Handle adding terms to a domain
    Requirements: 2.2, 2.4
    """
    try:
        path_params = get_path_parameters(event)
        domain_id = path_params.get('domain_id')
        
        if not domain_id:
            return create_error_response(400, 'Domain ID is required')
        
        # Verify domain exists and user owns it
        domain = execute_query_one(
            """
            SELECT id, metadata FROM tree_nodes 
            WHERE id = %s AND user_id = %s AND node_type = 'domain'
            """,
            (domain_id, user_id)
        )
        
        if not domain:
            return create_not_found_response('Domain not found')
        
        body = parse_request_body(event)
        terms = body.get('terms', [])
        
        if not terms or not isinstance(terms, list):
            return create_validation_error_response({
                'terms': 'Terms array is required'
            })
        
        validation_errors = {}
        processed_terms = []
        
        for i, term_data in enumerate(terms):
            if not isinstance(term_data, dict):
                validation_errors[f'terms[{i}]'] = 'Each term must be an object'
                continue
                
            term = term_data.get('term', '').strip()
            definition = term_data.get('definition', '').strip()
            
            if not term:
                validation_errors[f'terms[{i}].term'] = 'Term is required'
            elif len(term) < 2 or len(term) > 200:
                validation_errors[f'terms[{i}].term'] = 'Term must be between 2 and 200 characters'
                
            if not definition:
                validation_errors[f'terms[{i}].definition'] = 'Definition is required'
            elif len(definition) < 10 or len(definition) > 1000:
                validation_errors[f'terms[{i}].definition'] = 'Definition must be between 10 and 1000 characters'
            
            if term and definition:
                # Check for duplicate terms within this domain
                existing_term = execute_query_one(
                    """
                    SELECT id FROM tree_nodes 
                    WHERE parent_id = %s AND node_type = 'term' 
                    AND data->>'term' = %s
                    """,
                    (domain_id, term)
                )
                
                if existing_term:
                    validation_errors[f'terms[{i}].term'] = f'Term "{term}" already exists in this domain'
                else:
                    processed_terms.append({
                        'term': term,
                        'definition': definition
                    })
        
        if validation_errors:
            return create_validation_error_response(validation_errors)
        
        # Insert terms
        created_terms = []
        for term_data in processed_terms:
            term_id = str(uuid.uuid4())
            
            execute_query(
                """
                INSERT INTO tree_nodes (id, parent_id, user_id, node_type, data)
                VALUES (%s, %s, %s, 'term', %s)
                """,
                (term_id, domain_id, user_id, json.dumps(term_data))
            )
            
            created_terms.append({
                'id': term_id,
                'term': term_data['term'],
                'definition': term_data['definition']
            })
        
        # Update domain term count
        current_metadata = domain[1] if domain[1] else {}
        if isinstance(current_metadata, str):
            current_metadata = json.loads(current_metadata)
        
        current_metadata['term_count'] = current_metadata.get('term_count', 0) + len(created_terms)
        
        logger.info(f"Updating domain {domain_id} metadata: {current_metadata}")
        
        execute_query(
            """
            UPDATE tree_nodes 
            SET metadata = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (json.dumps(current_metadata), domain_id)
        )
        
        return create_created_response(
            {'terms': created_terms, 'count': len(created_terms)},
            f'{len(created_terms)} terms added successfully'
        )
        
    except Exception as e:
        logger.error(f"Error adding terms: {str(e)}")
        return handle_error(e)


def handle_get_terms(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle retrieving terms for a domain"""
    try:
        path_params = get_path_parameters(event)
        domain_id = path_params.get('domain_id')
        
        if not domain_id:
            return create_error_response(400, 'Domain ID is required')
        
        # Verify domain exists and user owns it
        domain = execute_query_one(
            """
            SELECT id FROM tree_nodes 
            WHERE id = %s AND user_id = %s AND node_type = 'domain'
            """,
            (domain_id, user_id)
        )
        
        if not domain:
            return create_not_found_response('Domain not found')
        
        # Get terms for the domain
        terms = execute_query(
            """
            SELECT 
                id,
                data->>'term' as term,
                data->>'definition' as definition,
                created_at,
                updated_at
            FROM tree_nodes
            WHERE parent_id = %s AND node_type = 'term'
            ORDER BY created_at ASC
            """,
            (domain_id,)
        )
        
        term_list = []
        for term in terms:
            term_list.append({
                'id': term[0],
                'term': term[1],
                'definition': term[2],
                'created_at': term[3].isoformat() if term[3] else None,
                'updated_at': term[4].isoformat() if term[4] else None
            })
        
        return create_success_response(term_list)
        
    except Exception as e:
        logger.error(f"Error retrieving terms: {str(e)}")
        return handle_error(e)


def handle_update_term(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle term updates"""
    try:
        path_params = get_path_parameters(event)
        domain_id = path_params.get('domain_id')
        term_id = path_params.get('term_id')
        
        if not domain_id or not term_id:
            return create_error_response(400, 'Domain ID and Term ID are required')
        
        # Verify domain ownership and term exists
        term = execute_query_one(
            """
            SELECT tn.data, d.user_id
            FROM tree_nodes tn
            JOIN tree_nodes d ON tn.parent_id = d.id
            WHERE tn.id = %s AND tn.parent_id = %s 
            AND tn.node_type = 'term' AND d.node_type = 'domain'
            """,
            (term_id, domain_id)
        )
        
        if not term or term[1] != user_id:
            return create_not_found_response('Term not found')
        
        body = parse_request_body(event)
        current_data = term[0]
        
        # Update fields if provided
        validation_errors = {}
        
        if 'term' in body:
            new_term = body['term'].strip()
            if len(new_term) < 2 or len(new_term) > 200:
                validation_errors['term'] = 'Term must be between 2 and 200 characters'
            else:
                # Check for duplicate terms within domain (excluding current term)
                duplicate = execute_query_one(
                    """
                    SELECT id FROM tree_nodes 
                    WHERE parent_id = %s AND node_type = 'term' 
                    AND data->>'term' = %s AND id != %s
                    """,
                    (domain_id, new_term, term_id)
                )
                
                if duplicate:
                    validation_errors['term'] = 'Term already exists in this domain'
                else:
                    current_data['term'] = new_term
        
        if 'definition' in body:
            new_definition = body['definition'].strip()
            if len(new_definition) < 10 or len(new_definition) > 1000:
                validation_errors['definition'] = 'Definition must be between 10 and 1000 characters'
            else:
                current_data['definition'] = new_definition
        
        if validation_errors:
            return create_validation_error_response(validation_errors)
        
        # Update term
        execute_query(
            """
            UPDATE tree_nodes 
            SET data = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (json.dumps(current_data), term_id)
        )
        
        return create_success_response({'id': term_id}, 'Term updated successfully')
        
    except Exception as e:
        logger.error(f"Error updating term: {str(e)}")
        return handle_error(e)


def handle_delete_term(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle term deletion"""
    try:
        path_params = get_path_parameters(event)
        domain_id = path_params.get('domain_id')
        term_id = path_params.get('term_id')
        
        if not domain_id or not term_id:
            return create_error_response(400, 'Domain ID and Term ID are required')
        
        # Verify domain ownership and term exists
        term = execute_query_one(
            """
            SELECT tn.id, d.user_id, d.metadata
            FROM tree_nodes tn
            JOIN tree_nodes d ON tn.parent_id = d.id
            WHERE tn.id = %s AND tn.parent_id = %s 
            AND tn.node_type = 'term' AND d.node_type = 'domain'
            """,
            (term_id, domain_id)
        )
        
        if not term or term[1] != user_id:
            return create_not_found_response('Term not found')
        
        # Delete term
        execute_query("DELETE FROM tree_nodes WHERE id = %s", (term_id,))
        
        # Update domain term count
        current_metadata = term[2] or {}
        current_metadata['term_count'] = max(0, current_metadata.get('term_count', 1) - 1)
        
        execute_query(
            """
            UPDATE tree_nodes 
            SET metadata = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (json.dumps(current_metadata), domain_id)
        )
        
        return create_success_response({'id': term_id}, 'Term deleted successfully')
        
    except Exception as e:
        logger.error(f"Error deleting term: {str(e)}")
        return handle_error(e)