"""
Post-confirmation Lambda trigger for Cognito User Pool
Creates user profile in database after successful confirmation
"""
import json
import logging
import os
import sys
from typing import Dict, Any

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
    Post-confirmation trigger to create user profile in database
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        Event (unchanged)
    """
    try:
        logger.info(f"Post-confirmation trigger called for user: {event.get('userName', 'unknown')}")
        logger.info(f"Trigger source: {event.get('triggerSource', 'unknown')}")
        
        # Only process actual confirmations
        if event.get('triggerSource') not in ['PostConfirmation_ConfirmSignUp', 'PostConfirmation_ConfirmForgotPassword']:
            logger.info("Skipping non-confirmation trigger")
            return event
        
        # Get user attributes
        user_attributes = event.get('request', {}).get('userAttributes', {})
        user_id = user_attributes.get('sub')  # Cognito user ID
        email = user_attributes.get('email', '')
        given_name = user_attributes.get('given_name', '')
        family_name = user_attributes.get('family_name', '')
        
        if not user_id or not email:
            logger.error("Missing required user attributes")
            raise Exception("Missing required user attributes")
        
        # Create user profile in database
        create_user_profile(user_id, email, given_name, family_name)
        
        logger.info(f"Successfully created user profile for: {user_id}")
        
        return event
        
    except Exception as e:
        logger.error(f"Post-confirmation trigger error: {str(e)}")
        # Don't raise exception here as user is already confirmed
        # Just log the error and continue
        return event


def create_user_profile(user_id: str, email: str, given_name: str = '', family_name: str = '') -> None:
    """
    Create user profile in PostgreSQL database
    
    Args:
        user_id: Cognito user ID (sub)
        email: User email address
        given_name: User's first name
        family_name: User's last name
    """
    db_connection = None
    
    try:
        # Get database connection
        secrets_client = SecretsClient()
        db_connection = DatabaseConnection(secrets_client)
        
        # Check if user already exists
        existing_user = db_connection.execute_query(
            "SELECT user_id FROM users WHERE cognito_user_id = %s",
            (user_id,)
        )
        
        if existing_user:
            logger.info(f"User profile already exists for: {user_id}")
            return
        
        # Insert new user profile
        db_connection.execute_query(
            """
            INSERT INTO users (cognito_user_id, email, first_name, last_name, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            """,
            (user_id, email, given_name, family_name)
        )
        
        logger.info(f"Created user profile in database for: {user_id}")
        
    except Exception as e:
        logger.error(f"Error creating user profile: {str(e)}")
        raise e
        
    finally:
        if db_connection:
            db_connection.close()