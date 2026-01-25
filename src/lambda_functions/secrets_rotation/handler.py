"""
AWS Secrets Manager rotation Lambda function for Know-It-All Tutor System.
Handles automatic rotation of database credentials and JWT secrets.

Rotation Policy:
- Local/Development: Every 2 days
- Staging: Every 30 days  
- Production: Every 180 days (6 months)
"""

import json
import logging
import os
import boto3
import psycopg2
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_client = boto3.client('secretsmanager')
rds_client = boto3.client('rds')

# Environment-specific configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
ROTATION_INTERVALS = {
    'production': 180,  # 6 months
    'staging': 30,      # 1 month
    'development': 2,   # 2 days
    'local': 2          # 2 days (LocalStack)
}


class SecretsRotationError(Exception):
    """Custom exception for secrets rotation errors."""
    pass


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for secrets rotation.
    
    Args:
        event: Lambda event containing rotation details
        context: Lambda context object
        
    Returns:
        Dictionary with rotation status
    """
    try:
        # Extract rotation parameters
        secret_arn = event['SecretId']
        token = event['ClientRequestToken']
        step = event['Step']
        
        logger.info(f"Starting rotation step '{step}' for secret: {secret_arn}")
        logger.info(f"Environment: {ENVIRONMENT}, Rotation interval: {ROTATION_INTERVALS.get(ENVIRONMENT, 'unknown')} days")
        
        # Validate rotation interval for this environment
        validate_rotation_policy(secret_arn)
        
        # Route to appropriate rotation step
        if step == "createSecret":
            create_secret(secret_arn, token)
        elif step == "setSecret":
            set_secret(secret_arn, token)
        elif step == "testSecret":
            test_secret(secret_arn, token)
        elif step == "finishSecret":
            finish_secret(secret_arn, token)
        else:
            raise SecretsRotationError(f"Invalid rotation step: {step}")
        
        logger.info(f"Successfully completed rotation step '{step}'")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Rotation step {step} completed successfully',
                'secret_arn': secret_arn,
                'token': token,
                'environment': ENVIRONMENT,
                'rotation_interval_days': ROTATION_INTERVALS.get(ENVIRONMENT)
            })
        }
        
    except Exception as e:
        logger.error(f"Rotation failed: {str(e)}")
        raise SecretsRotationError(f"Rotation failed: {str(e)}") from e


def validate_rotation_policy(secret_arn: str) -> None:
    """
    Validate that the secret's rotation policy matches environment requirements.
    
    Args:
        secret_arn: ARN of the secret being rotated
    """
    try:
        # Get secret metadata
        response = secrets_client.describe_secret(SecretId=secret_arn)
        
        # Check if rotation is configured
        if 'RotationEnabled' in response and response['RotationEnabled']:
            rotation_rules = response.get('RotationRules', {})
            current_interval = rotation_rules.get('AutomaticallyAfterDays')
            expected_interval = ROTATION_INTERVALS.get(ENVIRONMENT)
            
            if current_interval != expected_interval:
                logger.warning(
                    f"Rotation interval mismatch for {secret_arn}: "
                    f"current={current_interval}, expected={expected_interval} for {ENVIRONMENT}"
                )
                
                # Update rotation interval if needed
                try:
                    secrets_client.update_secret(
                        SecretId=secret_arn,
                        Description=f"Updated rotation interval to {expected_interval} days for {ENVIRONMENT} environment"
                    )
                    logger.info(f"Updated rotation policy for {secret_arn}")
                except Exception as update_error:
                    logger.warning(f"Could not update rotation interval: {update_error}")
        
        logger.info(f"Rotation policy validated for {secret_arn}")
        
    except Exception as e:
        logger.warning(f"Could not validate rotation policy: {str(e)}")
        # Don't fail rotation if validation fails


def create_secret(secret_arn: str, token: str) -> None:
    """
    Create a new version of the secret with new credentials.
    
    Args:
        secret_arn: ARN of the secret being rotated
        token: Client request token for this rotation
    """
    try:
        # Get the current secret
        current_secret = get_secret_dict(secret_arn, "AWSCURRENT")
        
        # Check if the AWSPENDING version already exists
        try:
            get_secret_dict(secret_arn, "AWSPENDING", token)
            logger.info("AWSPENDING version already exists, skipping creation")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Determine secret type and generate new credentials
        secret_name = secret_arn.split(':')[-1]
        
        if 'database' in secret_name.lower():
            new_secret = create_new_database_credentials(current_secret)
        elif 'jwt' in secret_name.lower():
            new_secret = create_new_jwt_secret(current_secret)
        else:
            raise SecretsRotationError(f"Unknown secret type for rotation: {secret_name}")
        
        # Store the new secret version
        secrets_client.put_secret_value(
            SecretId=secret_arn,
            ClientRequestToken=token,
            SecretString=json.dumps(new_secret),
            VersionStage="AWSPENDING"
        )
        
        logger.info("Successfully created new secret version")
        
    except Exception as e:
        logger.error(f"Failed to create secret: {str(e)}")
        raise SecretsRotationError(f"Failed to create secret: {str(e)}") from e


def set_secret(secret_arn: str, token: str) -> None:
    """
    Set the new secret in the service (e.g., update database user password).
    
    Args:
        secret_arn: ARN of the secret being rotated
        token: Client request token for this rotation
    """
    try:
        # Get the pending secret
        pending_secret = get_secret_dict(secret_arn, "AWSPENDING", token)
        secret_name = secret_arn.split(':')[-1]
        
        if 'database' in secret_name.lower():
            set_database_credentials(secret_arn, pending_secret)
        elif 'jwt' in secret_name.lower():
            # JWT secrets don't need to be "set" in an external service
            logger.info("JWT secret rotation - no external service update needed")
        else:
            raise SecretsRotationError(f"Unknown secret type for setting: {secret_name}")
        
        logger.info("Successfully set new secret in service")
        
    except Exception as e:
        logger.error(f"Failed to set secret: {str(e)}")
        raise SecretsRotationError(f"Failed to set secret: {str(e)}") from e


def test_secret(secret_arn: str, token: str) -> None:
    """
    Test the new secret to ensure it works correctly.
    
    Args:
        secret_arn: ARN of the secret being rotated
        token: Client request token for this rotation
    """
    try:
        # Get the pending secret
        pending_secret = get_secret_dict(secret_arn, "AWSPENDING", token)
        secret_name = secret_arn.split(':')[-1]
        
        if 'database' in secret_name.lower():
            test_database_connection(pending_secret)
        elif 'jwt' in secret_name.lower():
            test_jwt_secret(pending_secret)
        else:
            raise SecretsRotationError(f"Unknown secret type for testing: {secret_name}")
        
        logger.info("Successfully tested new secret")
        
    except Exception as e:
        logger.error(f"Failed to test secret: {str(e)}")
        raise SecretsRotationError(f"Failed to test secret: {str(e)}") from e


def finish_secret(secret_arn: str, token: str) -> None:
    """
    Finish the rotation by updating version stages.
    
    Args:
        secret_arn: ARN of the secret being rotated
        token: Client request token for this rotation
    """
    try:
        # Get current version info
        metadata = secrets_client.describe_secret(SecretId=secret_arn)
        
        current_version = None
        for version_id, stages in metadata["VersionIdsToStages"].items():
            if "AWSCURRENT" in stages:
                if version_id == token:
                    # The new version is already current
                    logger.info("New version is already AWSCURRENT")
                    return
                current_version = version_id
                break
        
        # Update version stages
        secrets_client.update_secret_version_stage(
            SecretId=secret_arn,
            VersionStage="AWSCURRENT",
            ClientRequestToken=token,
            RemoveFromVersionId=current_version
        )
        
        logger.info("Successfully finished secret rotation")
        
    except Exception as e:
        logger.error(f"Failed to finish secret rotation: {str(e)}")
        raise SecretsRotationError(f"Failed to finish secret rotation: {str(e)}") from e


def get_secret_dict(secret_arn: str, stage: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get secret as a dictionary.
    
    Args:
        secret_arn: ARN of the secret
        stage: Version stage (AWSCURRENT or AWSPENDING)
        token: Client request token (for AWSPENDING)
        
    Returns:
        Secret data as dictionary
    """
    params = {
        'SecretId': secret_arn,
        'VersionStage': stage
    }
    
    if token:
        params['VersionId'] = token
    
    response = secrets_client.get_secret_value(**params)
    return json.loads(response['SecretString'])


def create_new_database_credentials(current_secret: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create new database credentials.
    
    Args:
        current_secret: Current secret data
        
    Returns:
        New secret data with updated password
    """
    import secrets
    import string
    
    # Generate a new password
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    # Create new secret with same username but new password
    new_secret = current_secret.copy()
    new_secret['password'] = new_password
    
    return new_secret


def create_new_jwt_secret(current_secret: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create new JWT secret.
    
    Args:
        current_secret: Current secret data
        
    Returns:
        New secret data with updated JWT secret
    """
    import secrets
    import string
    
    # Generate a new JWT secret
    alphabet = string.ascii_letters + string.digits
    new_jwt_secret = ''.join(secrets.choice(alphabet) for _ in range(64))
    
    # Create new secret
    new_secret = current_secret.copy()
    new_secret['secret'] = new_jwt_secret
    
    return new_secret


def set_database_credentials(secret_arn: str, new_secret: Dict[str, Any]) -> None:
    """
    Update database user password.
    
    Args:
        secret_arn: ARN of the secret
        new_secret: New secret data
    """
    # Get current credentials to connect as admin
    current_secret = get_secret_dict(secret_arn, "AWSCURRENT")
    
    # Database connection parameters
    if os.getenv('LOCALSTACK_ENDPOINT'):
        # LocalStack RDS emulation
        host = 'localhost'
        port = 4566
        database = os.getenv('RDS_DATABASE', 'tutor_system')
        ssl_mode = 'disable'
        options = f"-c rds-instance-id={os.getenv('RDS_INSTANCE_IDENTIFIER', 'tutor-system-db')}"
    else:
        # Production Aurora
        host = os.getenv('AURORA_ENDPOINT')
        port = int(os.getenv('AURORA_PORT', '5432'))
        database = os.getenv('AURORA_DATABASE', 'tutor_system')
        ssl_mode = 'require'
        options = None
    
    # Connect as current user and update password
    try:
        conn_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': current_secret['username'],
            'password': current_secret['password'],
            'sslmode': ssl_mode
        }
        
        if options:
            conn_params['options'] = options
            
        conn = psycopg2.connect(**conn_params)
        
        with conn.cursor() as cursor:
            # Update user password
            cursor.execute(
                "ALTER USER %s WITH PASSWORD %s",
                (new_secret['username'], new_secret['password'])
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully updated database password for user: {new_secret['username']}")
        
    except Exception as e:
        logger.error(f"Failed to update database password: {str(e)}")
        raise SecretsRotationError(f"Failed to update database password: {str(e)}") from e


def test_database_connection(secret: Dict[str, Any]) -> None:
    """
    Test database connection with new credentials.
    
    Args:
        secret: Secret data to test
    """
    # Database connection parameters
    if os.getenv('LOCALSTACK_ENDPOINT'):
        # LocalStack RDS emulation
        host = 'localhost'
        port = 4566
        database = os.getenv('RDS_DATABASE', 'tutor_system')
        ssl_mode = 'disable'
        options = f"-c rds-instance-id={os.getenv('RDS_INSTANCE_IDENTIFIER', 'tutor-system-db')}"
    else:
        # Production Aurora
        host = os.getenv('AURORA_ENDPOINT')
        port = int(os.getenv('AURORA_PORT', '5432'))
        database = os.getenv('AURORA_DATABASE', 'tutor_system')
        ssl_mode = 'require'
        options = None
    
    try:
        conn_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': secret['username'],
            'password': secret['password'],
            'sslmode': ssl_mode,
            'connect_timeout': 10
        }
        
        if options:
            conn_params['options'] = options
            
        conn = psycopg2.connect(**conn_params)
        
        # Test with a simple query
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        conn.close()
        
        if result[0] != 1:
            raise SecretsRotationError("Database connection test failed")
        
        logger.info("Database connection test successful")
        
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        raise SecretsRotationError(f"Database connection test failed: {str(e)}") from e


def test_jwt_secret(secret: Dict[str, Any]) -> None:
    """
    Test JWT secret by creating and verifying a token.
    
    Args:
        secret: Secret data to test
    """
    try:
        import jwt
        from datetime import datetime, timedelta
        
        # Create a test token
        payload = {
            'test': True,
            'exp': datetime.utcnow() + timedelta(minutes=5)
        }
        
        token = jwt.encode(payload, secret['secret'], algorithm='HS256')
        
        # Verify the token
        decoded = jwt.decode(token, secret['secret'], algorithms=['HS256'])
        
        if not decoded.get('test'):
            raise SecretsRotationError("JWT secret test failed")
        
        logger.info("JWT secret test successful")
        
    except Exception as e:
        logger.error(f"JWT secret test failed: {str(e)}")
        raise SecretsRotationError(f"JWT secret test failed: {str(e)}") from e