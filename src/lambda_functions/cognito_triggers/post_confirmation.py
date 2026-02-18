"""
Post-confirmation Lambda trigger for Cognito User Pool
Creates user record in database after successful registration
"""
import json
import logging
import sys
import os
from typing import Dict, Any

# Add shared modules to path
sys.path.append('/opt/python')

from db_proxy_client import DBProxyClient

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DB Proxy client
db_proxy = DBProxyClient(os.environ.get('DB_PROXY_FUNCTION_NAME'))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Post-confirmation trigger to create user in database
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        Event (unchanged)
    """
    try:
        logger.info(f"Post-confirmation trigger for user: {event.get('userName')}")
        
        # Get user attributes
        user_attributes = event.get('request', {}).get('userAttributes', {})
        cognito_sub = event.get('userName')  # This is the Cognito sub
        email = user_attributes.get('email', '')
        first_name = user_attributes.get('given_name')
        last_name = user_attributes.get('family_name')
        
        # Create user record in database
        try:
            db_proxy.execute_query(
                """
                INSERT INTO users (cognito_sub, email, first_name, last_name, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (cognito_sub) DO NOTHING
                """,
                params=[cognito_sub, email, first_name or None, last_name or None, True]
            )
            logger.info(f"Created user record in database for {email}")
        except Exception as db_error:
            logger.error(f"Failed to create user in database: {db_error}")
            # Don't fail the confirmation if DB insert fails
        
        return event
        
    except Exception as e:
        logger.error(f"Post-confirmation trigger error: {e}", exc_info=True)
        # Return event anyway - don't block user confirmation
        return event
