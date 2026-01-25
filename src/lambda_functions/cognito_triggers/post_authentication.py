"""
Post-authentication Lambda trigger for Cognito User Pool
Logs successful authentication and updates user activity
"""
import json
import logging
import os
import sys
from typing import Dict, Any
from datetime import datetime

# Add shared modules to path
sys.path.append('/opt/python')
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from database import DatabaseConnection
from secrets_client import SecretsClient

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Post-authentication trigger for security logging and user activity tracking
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        Event (unchanged)
    """
    try:
        logger.info(f"Post-authentication trigger called for user: {event.get('userName', 'unknown')}")
        
        # Get user attributes and request info
        user_attributes = event.get('request', {}).get('userAttributes', {})
        user_id = user_attributes.get('sub')
        email = user_attributes.get('email', '')
        client_metadata = event.get('request', {}).get('clientMetadata', {})
        
        # Log successful authentication
        log_authentication_attempt(
            user_id=user_id,
            email=email,
            event_type='POST_AUTH',
            client_metadata=client_metadata,
            trigger_source=event.get('triggerSource', ''),
            success=True
        )
        
        # Update user's last login time
        update_user_last_login(user_id)
        
        return event
        
    except Exception as e:
        logger.error(f"Post-authentication trigger error: {str(e)}")
        # Don't block authentication for logging errors
        return event


def log_authentication_attempt(user_id: str, email: str, event_type: str, 
                             client_metadata: Dict[str, Any], trigger_source: str, 
                             success: bool) -> None:
    """
    Log authentication attempt to database for security monitoring
    
    Args:
        user_id: Cognito user ID
        email: User email
        event_type: Type of authentication event
        client_metadata: Client metadata from request
        trigger_source: Cognito trigger source
        success: Whether the attempt was successful
    """
    db_connection = None
    
    try:
        # Get database connection
        secrets_client = SecretsClient()
        db_connection = DatabaseConnection(secrets_client)
        
        # Insert authentication log
        db_connection.execute_query(
            """
            INSERT INTO auth_logs (
                cognito_user_id, email, event_type, trigger_source, 
                client_metadata, success, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (user_id, email, event_type, trigger_source, 
             json.dumps(client_metadata), success)
        )
        
        logger.info(f"Logged successful authentication for user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error logging authentication attempt: {str(e)}")
        
    finally:
        if db_connection:
            db_connection.close()


def update_user_last_login(user_id: str) -> None:
    """
    Update user's last login timestamp
    
    Args:
        user_id: Cognito user ID
    """
    db_connection = None
    
    try:
        # Get database connection
        secrets_client = SecretsClient()
        db_connection = DatabaseConnection(secrets_client)
        
        # Update last login time
        db_connection.execute_query(
            """
            UPDATE users 
            SET last_login_at = NOW(), updated_at = NOW()
            WHERE cognito_user_id = %s
            """,
            (user_id,)
        )
        
        logger.info(f"Updated last login time for user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error updating last login time: {str(e)}")
        
    finally:
        if db_connection:
            db_connection.close()