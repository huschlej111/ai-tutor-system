"""
Secrets Manager client for Know-It-All Tutor System
Handles encrypted credential retrieval using AWS Secrets Manager + KMS
"""
import json
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SecretsManagerClient:
    """Client for accessing encrypted secrets via AWS Secrets Manager"""
    
    def __init__(self, region: str = None, endpoint_url: str = None):
        """
        Initialize Secrets Manager client
        
        Args:
            region: AWS region (defaults to environment variable)
            endpoint_url: Custom endpoint for LocalStack (optional)
        """
        self.region = region or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.endpoint_url = endpoint_url or os.getenv('AWS_ENDPOINT_URL')
        
        # Configure boto3 client
        client_config = {
            'region_name': self.region
        }
        
        # Add endpoint URL for LocalStack
        if self.endpoint_url:
            client_config['endpoint_url'] = self.endpoint_url
            logger.info(f"Using LocalStack endpoint: {self.endpoint_url}")
        
        self.client = boto3.client('secretsmanager', **client_config)
        self._cache = {}  # Simple in-memory cache
    
    def get_secret(self, secret_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Retrieve and decrypt a secret from Secrets Manager
        
        Args:
            secret_name: Name/ARN of the secret
            use_cache: Whether to use cached values (default: True)
            
        Returns:
            Dictionary containing the secret data
            
        Raises:
            ClientError: If secret cannot be retrieved
            json.JSONDecodeError: If secret is not valid JSON
        """
        # Check cache first
        if use_cache and secret_name in self._cache:
            logger.debug(f"Using cached secret: {secret_name}")
            return self._cache[secret_name]
        
        try:
            logger.info(f"Retrieving secret: {secret_name}")
            
            # Get secret from Secrets Manager
            # This automatically handles KMS decryption
            response = self.client.get_secret_value(SecretId=secret_name)
            
            # Parse JSON secret string
            secret_data = json.loads(response['SecretString'])
            
            # Cache the result
            if use_cache:
                self._cache[secret_name] = secret_data
            
            logger.info(f"Successfully retrieved secret: {secret_name}")
            return secret_data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'DecryptionFailureException':
                logger.error(f"KMS decryption failed for secret: {secret_name}")
                raise Exception(f"Cannot decrypt secret {secret_name}. Check KMS permissions.")
            
            elif error_code == 'InternalServiceErrorException':
                logger.error(f"Internal service error retrieving secret: {secret_name}")
                raise Exception(f"AWS service error retrieving secret {secret_name}")
            
            elif error_code == 'InvalidParameterException':
                logger.error(f"Invalid parameter for secret: {secret_name}")
                raise Exception(f"Invalid secret name: {secret_name}")
            
            elif error_code == 'InvalidRequestException':
                logger.error(f"Invalid request for secret: {secret_name}")
                raise Exception(f"Invalid request for secret: {secret_name}")
            
            elif error_code == 'ResourceNotFoundException':
                logger.error(f"Secret not found: {secret_name}")
                raise Exception(f"Secret not found: {secret_name}")
            
            else:
                logger.error(f"Unexpected error retrieving secret {secret_name}: {e}")
                raise
        
        except json.JSONDecodeError as e:
            logger.error(f"Secret {secret_name} is not valid JSON: {e}")
            raise Exception(f"Secret {secret_name} contains invalid JSON")
    
    def get_database_credentials(self, environment: str = None) -> Dict[str, Any]:
        """
        Get database credentials for the specified environment
        
        Args:
            environment: Environment name (defaults to ENVIRONMENT env var)
            
        Returns:
            Dictionary with database connection parameters
        """
        env = environment or os.getenv('ENVIRONMENT', 'local')
        
        # For LocalStack, use the RDS credentials secret
        if os.getenv('LOCALSTACK_ENDPOINT'):
            secret_name = 'tutor-system/database/credentials'
        else:
            secret_name = f'tutor-system/database'
            if env != 'local':
                secret_name = f'tutor-system/{env}/database'
        
        return self.get_secret(secret_name)
    
    def get_jwt_config(self, environment: str = None) -> Dict[str, Any]:
        """
        Get JWT configuration for the specified environment
        
        Args:
            environment: Environment name (defaults to ENVIRONMENT env var)
            
        Returns:
            Dictionary with JWT configuration
        """
        env = environment or os.getenv('ENVIRONMENT', 'local')
        secret_name = f'tutor-system/jwt'
        
        if env != 'local':
            secret_name = f'tutor-system/{env}/jwt'
        
        return self.get_secret(secret_name)
    
    def get_ml_model_config(self, environment: str = None) -> Dict[str, Any]:
        """
        Get ML model configuration for the specified environment
        
        Args:
            environment: Environment name (defaults to ENVIRONMENT env var)
            
        Returns:
            Dictionary with ML model configuration
        """
        env = environment or os.getenv('ENVIRONMENT', 'local')
        secret_name = f'tutor-system/ml-model'
        
        if env != 'local':
            secret_name = f'tutor-system/{env}/ml-model'
        
        return self.get_secret(secret_name)
    
    def clear_cache(self):
        """Clear the secrets cache"""
        self._cache.clear()
        logger.info("Secrets cache cleared")
    
    def health_check(self) -> bool:
        """
        Perform a health check by attempting to list secrets
        
        Returns:
            True if Secrets Manager is accessible, False otherwise
        """
        try:
            self.client.list_secrets(MaxResults=1)
            return True
        except Exception as e:
            logger.error(f"Secrets Manager health check failed: {e}")
            return False


# Global instance for easy import
secrets_client = SecretsManagerClient()


def get_database_credentials() -> Dict[str, Any]:
    """Convenience function to get database credentials"""
    # Use LocalStack endpoint if available
    endpoint_url = os.getenv('LOCALSTACK_ENDPOINT', 'http://localhost:4566') if os.getenv('LOCALSTACK_ENDPOINT') else None
    client = SecretsManagerClient(endpoint_url=endpoint_url)
    return client.get_database_credentials()


def get_jwt_config() -> Dict[str, Any]:
    """Convenience function to get JWT configuration"""
    client = SecretsManagerClient()
    return client.get_jwt_config()


def get_ml_model_config() -> Dict[str, Any]:
    """Convenience function to get ML model configuration"""
    client = SecretsManagerClient()
    return client.get_ml_model_config()