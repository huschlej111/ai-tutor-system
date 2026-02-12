"""
Configuration management for Lambda functions
Handles environment variables and AWS Secrets Manager integration
"""
import os
import json
import boto3
from typing import Dict, Any, Optional
from functools import lru_cache


class ConfigManager:
    """Manages configuration from environment variables and AWS Secrets Manager"""
    
    def __init__(self):
        self.secrets_client = boto3.client('secretsmanager')
        self._cached_secrets: Dict[str, Dict[str, Any]] = {}
    
    @lru_cache(maxsize=128)
    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """Get secret from AWS Secrets Manager with caching"""
        if secret_name in self._cached_secrets:
            return self._cached_secrets[secret_name]
        
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            self._cached_secrets[secret_name] = secret_data
            return secret_data
        except Exception as e:
            print(f"Failed to retrieve secret {secret_name}: {e}")
            return {}
    
    def get_database_config(self) -> Dict[str, str]:
        """Get database configuration"""
        # Try to get from Secrets Manager first
        secret_name = os.environ.get('DB_SECRET_NAME', 'tutor-system/db-credentials')
        credentials = self.get_secret(secret_name)
        
        return {
            'host': os.environ.get('AURORA_ENDPOINT', ''),
            'port': os.environ.get('AURORA_PORT', '5432'),
            'database': os.environ.get('AURORA_DATABASE', 'tutor_system'),
            'user': credentials.get('username', os.environ.get('AURORA_USERNAME', '')),
            'password': credentials.get('password', os.environ.get('AURORA_PASSWORD', ''))
        }
    
    def get_jwt_config(self) -> Dict[str, str]:
        """Get JWT configuration"""
        secret_name = os.environ.get('JWT_SECRET_NAME', 'tutor-system/jwt-secret')
        jwt_secret = self.get_secret(secret_name)
        
        return {
            'secret': jwt_secret.get('secret', os.environ.get('JWT_SECRET', '')),
            'algorithm': os.environ.get('JWT_ALGORITHM', 'HS256'),
            'expiration_hours': int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))
        }
    
    def get_model_config(self) -> Dict[str, str]:
        """Get ML model configuration"""
        return {
            'model_path': os.environ.get('MODEL_PATH', '/opt/final_similarity_model'),
            'similarity_threshold': float(os.environ.get('SIMILARITY_THRESHOLD', '0.7')),
            'batch_size': int(os.environ.get('MODEL_BATCH_SIZE', '32'))
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return {
            'cors_origins': os.environ.get('CORS_ORIGINS', '*').split(','),
            'rate_limit': int(os.environ.get('RATE_LIMIT', '1000')),
            'max_request_size': int(os.environ.get('MAX_REQUEST_SIZE', '1048576'))  # 1MB
        }
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return os.environ.get('ENVIRONMENT', 'production').lower() == 'development'
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return os.environ.get('ENVIRONMENT', 'production').lower() == 'production'


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """Get the global configuration manager"""
    return config_manager


def get_env_var(key: str, default: str = None, required: bool = False) -> str:
    """Get environment variable with optional default and required validation"""
    value = os.environ.get(key, default)
    
    if required and not value:
        raise ValueError(f"Required environment variable {key} is not set")
    
    return value


def get_secret_value(secret_name: str, key: str = None) -> Any:
    """Get value from AWS Secrets Manager"""
    secret_data = config_manager.get_secret(secret_name)
    
    if key:
        return secret_data.get(key)
    
    return secret_data