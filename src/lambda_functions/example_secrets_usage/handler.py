"""
Example Lambda function showing how to use Secrets Manager + KMS
This demonstrates the proper way to access encrypted credentials
"""
import json
import sys
import os

# Add the shared modules to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from secrets_client import get_database_credentials, get_jwt_config
from database import get_db_cursor, health_check
from response_utils import create_response
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Example Lambda function that uses Secrets Manager + KMS for credentials
    
    This function demonstrates:
    1. Retrieving encrypted credentials from Secrets Manager
    2. Using those credentials to connect to the database
    3. Proper error handling and logging
    """
    
    try:
        logger.info("Starting example Lambda function")
        
        # 1. Get database credentials from Secrets Manager (KMS encrypted)
        logger.info("Retrieving database credentials from Secrets Manager")
        db_creds = get_database_credentials()
        
        logger.info(f"Connected to database: {db_creds.get('database')} at {db_creds.get('host')}")
        
        # 2. Get JWT configuration from Secrets Manager (KMS encrypted)
        logger.info("Retrieving JWT configuration from Secrets Manager")
        jwt_config = get_jwt_config()
        
        logger.info(f"JWT algorithm: {jwt_config.get('algorithm')}")
        
        # 3. Test database connectivity using the encrypted credentials
        logger.info("Testing database connectivity")
        if not health_check():
            logger.error("Database health check failed")
            return create_response(500, {
                'error': 'Database connectivity failed',
                'message': 'Could not connect to database using Secrets Manager credentials'
            })
        
        # 4. Example database query using encrypted credentials
        logger.info("Executing example database query")
        with get_db_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as user_count FROM users")
            result = cursor.fetchone()
            user_count = result[0] if result else 0
        
        # 5. Return success response
        response_data = {
            'message': 'Successfully accessed encrypted credentials',
            'database': {
                'host': db_creds.get('host'),
                'database': db_creds.get('database'),
                'connection_status': 'healthy',
                'user_count': user_count
            },
            'jwt': {
                'algorithm': jwt_config.get('algorithm'),
                'expiration_hours': jwt_config.get('expiration_hours')
            },
            'security': {
                'credentials_source': 'AWS Secrets Manager',
                'encryption': 'KMS encrypted',
                'environment': os.getenv('ENVIRONMENT', 'unknown')
            }
        }
        
        logger.info("Example Lambda function completed successfully")
        return create_response(200, response_data)
        
    except Exception as e:
        logger.error(f"Lambda function failed: {str(e)}")
        
        return create_response(500, {
            'error': 'Internal server error',
            'message': 'Failed to access encrypted credentials',
            'details': str(e) if os.getenv('ENVIRONMENT') == 'local' else 'Contact support'
        })


def test_locally():
    """Test function for local development"""
    print("🧪 Testing Lambda function locally with LocalStack")
    
    # Set up LocalStack environment
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['ENVIRONMENT'] = 'local'
    
    # Create a test event
    test_event = {
        'httpMethod': 'GET',
        'path': '/test-secrets',
        'headers': {},
        'body': None
    }
    
    # Create a test context
    class TestContext:
        def __init__(self):
            self.function_name = 'test-secrets-function'
            self.function_version = '1'
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:000000000000:function:test'
            self.memory_limit_in_mb = 128
            self.remaining_time_in_millis = 30000
    
    context = TestContext()
    
    # Call the Lambda function
    try:
        result = lambda_handler(test_event, context)
        
        print("✅ Lambda function executed successfully!")
        print(f"Status Code: {result['statusCode']}")
        
        body = json.loads(result['body'])
        print(f"Database: {body['database']['database']} ({body['database']['connection_status']})")
        print(f"Users: {body['database']['user_count']}")
        print(f"JWT Algorithm: {body['jwt']['algorithm']}")
        print(f"Security: {body['security']['credentials_source']} with {body['security']['encryption']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda function failed: {e}")
        return False


if __name__ == "__main__":
    # Run local test when script is executed directly
    test_locally()