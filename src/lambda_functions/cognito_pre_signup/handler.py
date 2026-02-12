"""
Cognito Pre-SignUp Trigger
Auto-confirms users and auto-verifies email
"""
import json


def lambda_handler(event, context):
    """
    Pre-SignUp trigger - auto-confirm all users
    """
    print(f"Pre-SignUp trigger event: {json.dumps(event)}")
    
    # Auto-confirm the user
    event['response']['autoConfirmUser'] = True
    
    # Auto-verify email
    event['response']['autoVerifyEmail'] = True
    
    print(f"Auto-confirming user: {event['request']['userAttributes'].get('email')}")
    
    return event
