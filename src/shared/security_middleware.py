"""
Security middleware for API Gateway Lambda functions
Implements security headers, input validation, and request sanitization
"""
import json
import re
import html
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Security configuration
SECURITY_CONFIG = {
    'max_request_size': 10 * 1024 * 1024,  # 10MB max request size
    'max_string_length': 10000,  # Max length for string fields
    'max_array_length': 1000,   # Max length for arrays
    'allowed_content_types': [
        'application/json',
        'multipart/form-data',
        'application/x-www-form-urlencoded'
    ],
    'rate_limit_headers': True,
    'security_headers': {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';",
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }
}


class SecurityValidationError(Exception):
    """Custom exception for security validation errors"""
    pass


def add_security_headers(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add security headers to API Gateway response
    """
    if 'headers' not in response:
        response['headers'] = {}
    
    # Add security headers
    response['headers'].update(SECURITY_CONFIG['security_headers'])
    
    # Add CORS headers if not present
    cors_headers = {
        'Access-Control-Allow-Origin': '*',  # Should be restricted in production
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Max-Age': '86400'
    }
    
    for header, value in cors_headers.items():
        if header not in response['headers']:
            response['headers'][header] = value
    
    # Add timestamp header
    response['headers']['X-Timestamp'] = datetime.now(timezone.utc).isoformat()
    
    return response


def validate_request_size(event: Dict[str, Any]) -> None:
    """
    Validate request size limits
    """
    body = event.get('body', '')
    if body:
        body_size = len(body.encode('utf-8'))
        if body_size > SECURITY_CONFIG['max_request_size']:
            raise SecurityValidationError(
                f"Request body too large: {body_size} bytes (max: {SECURITY_CONFIG['max_request_size']} bytes)"
            )


def validate_content_type(event: Dict[str, Any]) -> None:
    """
    Validate request content type
    """
    headers = event.get('headers', {})
    content_type = headers.get('Content-Type', '') or headers.get('content-type', '')
    
    if content_type:
        # Extract base content type (ignore charset, boundary, etc.)
        base_content_type = content_type.split(';')[0].strip().lower()
        
        if base_content_type not in SECURITY_CONFIG['allowed_content_types']:
            raise SecurityValidationError(f"Unsupported content type: {content_type}")


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input to prevent XSS and injection attacks
    """
    if not isinstance(value, str):
        return str(value)
    
    # Use configured max length if not specified
    if max_length is None:
        max_length = SECURITY_CONFIG['max_string_length']
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
    
    # HTML escape to prevent XSS
    value = html.escape(value, quote=True)
    
    # Remove null bytes and control characters (except newlines and tabs)
    value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
    
    # Remove potentially dangerous SQL patterns (basic protection)
    sql_patterns = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)',
        r'(--|/\*|\*/)',
        r'(\bUNION\b.*\bSELECT\b)',
        r'(\bOR\b.*=.*\bOR\b)',
        r'(\bAND\b.*=.*\bAND\b)'
    ]
    
    for pattern in sql_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    return value.strip()


def sanitize_data(data: Any, max_depth: int = 10) -> Any:
    """
    Recursively sanitize data structure
    """
    if max_depth <= 0:
        raise SecurityValidationError("Data structure too deeply nested")
    
    if isinstance(data, dict):
        if len(data) > SECURITY_CONFIG['max_array_length']:
            raise SecurityValidationError(f"Object has too many keys: {len(data)}")
        
        sanitized = {}
        for key, value in data.items():
            # Sanitize key
            clean_key = sanitize_string(str(key), 100)  # Limit key length
            sanitized[clean_key] = sanitize_data(value, max_depth - 1)
        return sanitized
    
    elif isinstance(data, list):
        if len(data) > SECURITY_CONFIG['max_array_length']:
            raise SecurityValidationError(f"Array too long: {len(data)}")
        
        return [sanitize_data(item, max_depth - 1) for item in data]
    
    elif isinstance(data, str):
        return sanitize_string(data)
    
    elif isinstance(data, (int, float, bool)) or data is None:
        return data
    
    else:
        # Convert unknown types to string and sanitize
        return sanitize_string(str(data))


def validate_json_structure(data: Dict[str, Any], required_fields: List[str] = None) -> None:
    """
    Validate JSON structure and required fields
    """
    if not isinstance(data, dict):
        raise SecurityValidationError("Request body must be a JSON object")
    
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise SecurityValidationError(f"Missing required fields: {', '.join(missing_fields)}")


def validate_email(email: str) -> bool:
    """
    Validate email format and length
    """
    if not email or len(email) > 254:  # RFC 5321 limit
        return False
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def validate_uuid(uuid_str: str) -> bool:
    """
    Validate UUID format
    """
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    return re.match(uuid_pattern, uuid_str.lower()) is not None


def security_middleware(func):
    """
    Decorator to apply security middleware to Lambda functions
    """
    def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        try:
            # Validate request size
            validate_request_size(event)
            
            # Validate content type for POST/PUT requests
            http_method = event.get('httpMethod', '').upper()
            if http_method in ['POST', 'PUT', 'PATCH']:
                validate_content_type(event)
            
            # Parse and sanitize request body if present
            if event.get('body'):
                try:
                    body_data = json.loads(event['body'])
                    sanitized_data = sanitize_data(body_data)
                    event['body'] = json.dumps(sanitized_data)
                    event['sanitized_body'] = sanitized_data
                except json.JSONDecodeError:
                    raise SecurityValidationError("Invalid JSON in request body")
            
            # Sanitize path parameters
            if event.get('pathParameters'):
                sanitized_params = {}
                for key, value in event['pathParameters'].items():
                    sanitized_params[sanitize_string(key, 50)] = sanitize_string(value, 200)
                event['pathParameters'] = sanitized_params
            
            # Sanitize query parameters
            if event.get('queryStringParameters'):
                sanitized_query = {}
                for key, value in event['queryStringParameters'].items():
                    sanitized_query[sanitize_string(key, 50)] = sanitize_string(value, 500)
                event['queryStringParameters'] = sanitized_query
            
            # Call the original function
            response = func(event, context)
            
            # Add security headers to response
            response = add_security_headers(response)
            
            return response
            
        except SecurityValidationError as e:
            logger.warning(f"Security validation error: {str(e)}")
            return add_security_headers({
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            })
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            return add_security_headers({
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Internal Server Error',
                    'message': 'An unexpected error occurred',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            })
    
    return wrapper


def create_secure_response(status_code: int, body: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Create a secure API Gateway response with proper headers
    """
    response = {
        'statusCode': status_code,
        'headers': headers or {},
        'body': json.dumps(body, default=str)
    }
    
    return add_security_headers(response)


def validate_input_patterns(data: Dict[str, Any], patterns: Dict[str, str]) -> None:
    """
    Validate input data against regex patterns
    """
    for field, pattern in patterns.items():
        if field in data:
            value = str(data[field])
            if not re.match(pattern, value):
                raise SecurityValidationError(f"Invalid format for field '{field}'")


def check_rate_limit_headers(event: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate rate limit headers based on user context
    """
    headers = {}
    
    if SECURITY_CONFIG['rate_limit_headers']:
        # Extract user info from Cognito context if available
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        
        user_groups = claims.get('cognito:groups', '').split(',') if claims.get('cognito:groups') else []
        
        # Set rate limits based on user groups
        if 'admin' in user_groups:
            headers.update({
                'X-RateLimit-Limit': '500',
                'X-RateLimit-Remaining': '500',
                'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
            })
        elif 'instructor' in user_groups:
            headers.update({
                'X-RateLimit-Limit': '200',
                'X-RateLimit-Remaining': '200',
                'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
            })
        else:
            headers.update({
                'X-RateLimit-Limit': '100',
                'X-RateLimit-Remaining': '100',
                'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
            })
    
    return headers