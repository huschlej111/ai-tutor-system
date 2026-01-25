"""
Pre-signup Lambda trigger for Cognito User Pool
Validates user registration and auto-confirms users
"""
import json
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Pre-signup trigger for user validation
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        Modified event with response
    """
    try:
        logger.info(f"Pre-signup trigger called for user: {event.get('userName', 'unknown')}")
        logger.info(f"Trigger source: {event.get('triggerSource', 'unknown')}")
        
        # Get user attributes
        user_attributes = event.get('request', {}).get('userAttributes', {})
        email = user_attributes.get('email', '')
        
        # Validate email format (basic validation)
        if not email or '@' not in email:
            logger.error(f"Invalid email format: {email}")
            raise Exception("Invalid email format")
        
        # Auto-confirm users for development environment
        # In production, you might want to require email verification
        if event.get('triggerSource') == 'PreSignUp_SignUp':
            event['response']['autoConfirmUser'] = True
            event['response']['autoVerifyEmail'] = True
            
            logger.info(f"Auto-confirming user: {event.get('userName')}")
        
        # Additional validation can be added here
        # For example, checking against a whitelist or blacklist
        
        return event
        
    except Exception as e:
        logger.error(f"Pre-signup trigger error: {str(e)}")
        # Re-raise the exception to prevent user registration
        raise e