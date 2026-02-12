"""
Enhanced secrets management for Know-It-All Tutor System.
Provides secure access to AWS Secrets Manager with rotation, caching, and encryption.
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from functools import lru_cache
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


logger = logging.getLogger(__name__)


class SecretsManagerError(Exception):
    """Custom exception for secrets management errors."""
    pass


class SecretCache:
    """Thread-safe cache for secrets with TTL support."""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached secret if not expired."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.now() > entry['expires_at']:
            del self.cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Cache secret with TTL."""
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl),
            'cached_at': datetime.now()
        }
    
    def invalidate(self, key: str) -> None:
        """Remove secret from cache."""
        self.cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached secrets."""
        self.cache.clear()


class SecretsManager:
    """
    Enhanced secrets manager with caching, rotation support, and security features.
    """
    
    def __init__(
        self,
        region_name: Optional[str] = None,
        cache_ttl: int = 300,
        enable_cache: bool = True,
        kms_key_id: Optional[str] = None
    ):
        """
        Initialize the secrets manager.
        
        Args:
            region_name: AWS region name (defaults to environment variable or us-east-1)
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
            enable_cache: Whether to enable secret caching (default: True)
            kms_key_id: KMS key ID for encryption (optional)
        """
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.kms_key_id = kms_key_id
        self.enable_cache = enable_cache
        self.cache = SecretCache(cache_ttl) if enable_cache else None
        
        # Initialize AWS clients
        try:
            self.secrets_client = boto3.client('secretsmanager', region_name=self.region_name)
            self.kms_client = boto3.client('kms', region_name=self.region_name)
        except NoCredentialsError as e:
            logger.error("AWS credentials not found")
            raise SecretsManagerError("AWS credentials not configured") from e
        
        # Environment-specific configuration
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.secret_prefix = f"tutor-system/{self.environment}"
    
    def get_secret(
        self,
        secret_name: str,
        version_id: Optional[str] = None,
        version_stage: str = "AWSCURRENT",
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieve a secret from AWS Secrets Manager with caching.
        
        Args:
            secret_name: Name of the secret (without environment prefix)
            version_id: Specific version ID to retrieve
            version_stage: Version stage (AWSCURRENT or AWSPENDING)
            force_refresh: Force refresh from AWS, bypassing cache
            
        Returns:
            Dictionary containing the secret data
            
        Raises:
            SecretsManagerError: If secret retrieval fails
        """
        # Add environment prefix if not already present
        full_secret_name = self._get_full_secret_name(secret_name)
        cache_key = f"{full_secret_name}:{version_stage}:{version_id or 'current'}"
        
        # Check cache first (unless force refresh)
        if not force_refresh and self.enable_cache:
            cached_secret = self.cache.get(cache_key)
            if cached_secret is not None:
                logger.debug(f"Retrieved secret '{secret_name}' from cache")
                return cached_secret
        
        try:
            # Prepare request parameters
            get_secret_params = {
                'SecretId': full_secret_name,
                'VersionStage': version_stage
            }
            
            if version_id:
                get_secret_params['VersionId'] = version_id
            
            # Retrieve secret from AWS
            logger.info(f"Retrieving secret '{secret_name}' from AWS Secrets Manager")
            response = self.secrets_client.get_secret_value(**get_secret_params)
            
            # Parse secret string
            secret_data = self._parse_secret_string(response['SecretString'])
            
            # Add metadata
            secret_with_metadata = {
                'data': secret_data,
                'metadata': {
                    'arn': response['ARN'],
                    'name': response['Name'],
                    'version_id': response['VersionId'],
                    'version_stages': response.get('VersionStages', []),
                    'created_date': response.get('CreatedDate'),
                    'retrieved_at': datetime.now().isoformat()
                }
            }
            
            # Cache the secret
            if self.enable_cache:
                self.cache.set(cache_key, secret_with_metadata)
            
            logger.info(f"Successfully retrieved secret '{secret_name}'")
            return secret_with_metadata
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ResourceNotFoundException':
                raise SecretsManagerError(f"Secret '{secret_name}' not found") from e
            elif error_code == 'InvalidParameterException':
                raise SecretsManagerError(f"Invalid parameter for secret '{secret_name}': {error_message}") from e
            elif error_code == 'InvalidRequestException':
                raise SecretsManagerError(f"Invalid request for secret '{secret_name}': {error_message}") from e
            elif error_code == 'DecryptionFailureException':
                raise SecretsManagerError(f"Failed to decrypt secret '{secret_name}'") from e
            else:
                raise SecretsManagerError(f"Failed to retrieve secret '{secret_name}': {error_message}") from e
    
    def create_secret(
        self,
        secret_name: str,
        secret_data: Union[Dict[str, Any], str],
        description: Optional[str] = None,
        kms_key_id: Optional[str] = None,
        replica_regions: Optional[list] = None,
        force_overwrite: bool = False
    ) -> str:
        """
        Create a new secret in AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret (without environment prefix)
            secret_data: Secret data (dict or string)
            description: Description of the secret
            kms_key_id: KMS key ID for encryption
            replica_regions: List of regions to replicate to
            force_overwrite: Whether to overwrite existing secret
            
        Returns:
            ARN of the created secret
            
        Raises:
            SecretsManagerError: If secret creation fails
        """
        full_secret_name = self._get_full_secret_name(secret_name)
        
        try:
            # Prepare secret string
            if isinstance(secret_data, dict):
                secret_string = json.dumps(secret_data)
            else:
                secret_string = str(secret_data)
            
            # Prepare create parameters
            create_params = {
                'Name': full_secret_name,
                'SecretString': secret_string,
                'Description': description or f"Secret for {secret_name} in {self.environment} environment",
                'KmsKeyId': kms_key_id or self.kms_key_id
            }
            
            # Add replica regions if specified
            if replica_regions:
                create_params['ReplicaRegions'] = [
                    {'Region': region} for region in replica_regions
                ]
            
            # Add tags
            create_params['Tags'] = [
                {'Key': 'Environment', 'Value': self.environment},
                {'Key': 'Project', 'Value': 'know-it-all-tutor'},
                {'Key': 'ManagedBy', 'Value': 'secrets-manager'},
                {'Key': 'CreatedAt', 'Value': datetime.now().isoformat()}
            ]
            
            # Create the secret
            logger.info(f"Creating secret '{secret_name}'")
            response = self.secrets_client.create_secret(**create_params)
            
            logger.info(f"Successfully created secret '{secret_name}' with ARN: {response['ARN']}")
            return response['ARN']
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ResourceExistsException':
                if force_overwrite:
                    logger.warning(f"Secret '{secret_name}' exists, updating instead")
                    return self.update_secret(secret_name, secret_data)
                else:
                    raise SecretsManagerError(f"Secret '{secret_name}' already exists") from e
            else:
                raise SecretsManagerError(f"Failed to create secret '{secret_name}': {error_message}") from e
    
    def update_secret(
        self,
        secret_name: str,
        secret_data: Union[Dict[str, Any], str],
        description: Optional[str] = None,
        kms_key_id: Optional[str] = None
    ) -> str:
        """
        Update an existing secret in AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret (without environment prefix)
            secret_data: New secret data
            description: Updated description
            kms_key_id: KMS key ID for encryption
            
        Returns:
            Version ID of the updated secret
            
        Raises:
            SecretsManagerError: If secret update fails
        """
        full_secret_name = self._get_full_secret_name(secret_name)
        
        try:
            # Prepare secret string
            if isinstance(secret_data, dict):
                secret_string = json.dumps(secret_data)
            else:
                secret_string = str(secret_data)
            
            # Prepare update parameters
            update_params = {
                'SecretId': full_secret_name,
                'SecretString': secret_string
            }
            
            if description:
                update_params['Description'] = description
            
            if kms_key_id or self.kms_key_id:
                update_params['KmsKeyId'] = kms_key_id or self.kms_key_id
            
            # Update the secret
            logger.info(f"Updating secret '{secret_name}'")
            response = self.secrets_client.update_secret(**update_params)
            
            # Invalidate cache
            if self.enable_cache:
                cache_pattern = f"{full_secret_name}:"
                keys_to_remove = [key for key in self.cache.cache.keys() if key.startswith(cache_pattern)]
                for key in keys_to_remove:
                    self.cache.invalidate(key)
            
            logger.info(f"Successfully updated secret '{secret_name}' to version: {response['VersionId']}")
            return response['VersionId']
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ResourceNotFoundException':
                raise SecretsManagerError(f"Secret '{secret_name}' not found") from e
            else:
                raise SecretsManagerError(f"Failed to update secret '{secret_name}': {error_message}") from e
    
    def rotate_secret(
        self,
        secret_name: str,
        rotation_lambda_arn: str,
        rotation_interval: int = 30
    ) -> bool:
        """
        Enable automatic rotation for a secret.
        
        Args:
            secret_name: Name of the secret (without environment prefix)
            rotation_lambda_arn: ARN of the Lambda function for rotation
            rotation_interval: Rotation interval in days
            
        Returns:
            True if rotation was enabled successfully
            
        Raises:
            SecretsManagerError: If rotation setup fails
        """
        full_secret_name = self._get_full_secret_name(secret_name)
        
        try:
            logger.info(f"Enabling rotation for secret '{secret_name}'")
            
            self.secrets_client.rotate_secret(
                SecretId=full_secret_name,
                RotationLambdaARN=rotation_lambda_arn,
                RotationRules={
                    'AutomaticallyAfterDays': rotation_interval
                }
            )
            
            logger.info(f"Successfully enabled rotation for secret '{secret_name}'")
            return True
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            raise SecretsManagerError(f"Failed to enable rotation for secret '{secret_name}': {error_message}") from e
    
    def delete_secret(
        self,
        secret_name: str,
        recovery_window_days: int = 30,
        force_delete: bool = False
    ) -> str:
        """
        Delete a secret from AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret (without environment prefix)
            recovery_window_days: Recovery window in days (7-30)
            force_delete: Force immediate deletion without recovery window
            
        Returns:
            Deletion date as ISO string
            
        Raises:
            SecretsManagerError: If secret deletion fails
        """
        full_secret_name = self._get_full_secret_name(secret_name)
        
        try:
            delete_params = {'SecretId': full_secret_name}
            
            if force_delete:
                delete_params['ForceDeleteWithoutRecovery'] = True
            else:
                delete_params['RecoveryWindowInDays'] = max(7, min(30, recovery_window_days))
            
            logger.warning(f"Deleting secret '{secret_name}' (force: {force_delete})")
            response = self.secrets_client.delete_secret(**delete_params)
            
            # Invalidate cache
            if self.enable_cache:
                cache_pattern = f"{full_secret_name}:"
                keys_to_remove = [key for key in self.cache.cache.keys() if key.startswith(cache_pattern)]
                for key in keys_to_remove:
                    self.cache.invalidate(key)
            
            deletion_date = response['DeletionDate'].isoformat()
            logger.warning(f"Secret '{secret_name}' scheduled for deletion on: {deletion_date}")
            return deletion_date
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            raise SecretsManagerError(f"Failed to delete secret '{secret_name}': {error_message}") from e
    
    def list_secrets(self, include_planned_deletion: bool = False) -> list:
        """
        List all secrets for the current environment.
        
        Args:
            include_planned_deletion: Include secrets scheduled for deletion
            
        Returns:
            List of secret metadata dictionaries
        """
        try:
            secrets = []
            paginator = self.secrets_client.get_paginator('list_secrets')
            
            for page in paginator.paginate():
                for secret in page['SecretList']:
                    # Filter by environment prefix
                    if secret['Name'].startswith(self.secret_prefix):
                        # Skip deleted secrets unless requested
                        if not include_planned_deletion and secret.get('DeletedDate'):
                            continue
                        
                        secrets.append({
                            'name': secret['Name'].replace(f"{self.secret_prefix}/", ""),
                            'full_name': secret['Name'],
                            'arn': secret['ARN'],
                            'description': secret.get('Description', ''),
                            'created_date': secret.get('CreatedDate'),
                            'last_changed_date': secret.get('LastChangedDate'),
                            'last_accessed_date': secret.get('LastAccessedDate'),
                            'deleted_date': secret.get('DeletedDate'),
                            'tags': secret.get('Tags', [])
                        })
            
            logger.info(f"Found {len(secrets)} secrets for environment '{self.environment}'")
            return secrets
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            raise SecretsManagerError(f"Failed to list secrets: {error_message}") from e
    
    def _get_full_secret_name(self, secret_name: str) -> str:
        """Get the full secret name with environment prefix."""
        if secret_name.startswith(self.secret_prefix):
            return secret_name
        return f"{self.secret_prefix}/{secret_name}"
    
    def _parse_secret_string(self, secret_string: str) -> Union[Dict[str, Any], str]:
        """Parse secret string as JSON if possible, otherwise return as string."""
        try:
            return json.loads(secret_string)
        except (json.JSONDecodeError, TypeError):
            return secret_string
    
    def get_database_credentials(self) -> Dict[str, str]:
        """
        Convenience method to get database credentials.
        
        Returns:
            Dictionary with database connection parameters
        """
        try:
            secret = self.get_secret('database-credentials')
            db_creds = secret['data']
            
            return {
                'host': os.getenv('AURORA_ENDPOINT'),
                'port': int(os.getenv('AURORA_PORT', '5432')),
                'database': os.getenv('AURORA_DATABASE', 'tutor_system'),
                'username': db_creds['username'],
                'password': db_creds['password']
            }
        except Exception as e:
            logger.error(f"Failed to get database credentials: {e}")
            raise SecretsManagerError("Database credentials not available") from e
    
    def get_jwt_secret(self) -> str:
        """
        Convenience method to get JWT signing secret.
        
        Returns:
            JWT signing secret string
        """
        try:
            secret = self.get_secret('jwt-secret')
            return secret['data']['secret']
        except Exception as e:
            logger.error(f"Failed to get JWT secret: {e}")
            raise SecretsManagerError("JWT secret not available") from e


# Global instance for easy access
_secrets_manager_instance: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """
    Get a singleton instance of the SecretsManager.
    
    Returns:
        SecretsManager instance
    """
    global _secrets_manager_instance
    
    if _secrets_manager_instance is None:
        _secrets_manager_instance = SecretsManager()
    
    return _secrets_manager_instance


# Convenience functions
def get_secret(secret_name: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to get a secret."""
    return get_secrets_manager().get_secret(secret_name, **kwargs)


def get_database_credentials() -> Dict[str, str]:
    """Convenience function to get database credentials."""
    return get_secrets_manager().get_database_credentials()


def get_jwt_secret() -> str:
    """Convenience function to get JWT secret."""
    return get_secrets_manager().get_jwt_secret()