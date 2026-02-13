"""
Unit tests for secrets_client module
Tests AWS Secrets Manager client
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.secrets_client import SecretsManagerClient


@pytest.mark.unit
class TestSecretsManagerClient:
    """Test SecretsManagerClient class"""
    
    @patch('shared.secrets_client.boto3.client')
    def test_init_default(self, mock_boto):
        """Test client initialization with defaults"""
        client = SecretsManagerClient()
        
        assert client.region == 'us-east-1'
        mock_boto.assert_called_once()
    
    @patch('shared.secrets_client.boto3.client')
    def test_init_with_region(self, mock_boto):
        """Test client initialization with custom region"""
        client = SecretsManagerClient(region='us-west-2')
        
        assert client.region == 'us-west-2'
    
    @patch('shared.secrets_client.boto3.client')
    def test_init_with_endpoint(self, mock_boto):
        """Test client initialization with custom endpoint"""
        client = SecretsManagerClient(endpoint_url='http://localhost:4566')
        
        assert client.endpoint_url == 'http://localhost:4566'
    
    @patch('shared.secrets_client.boto3.client')
    def test_get_secret_success(self, mock_boto):
        """Test successfully retrieving a secret"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': '{"username": "admin", "password": "secret123"}'
        }
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        result = client.get_secret('test-secret')
        
        assert result['username'] == 'admin'
        assert result['password'] == 'secret123'
    
    @patch('shared.secrets_client.boto3.client')
    def test_get_secret_with_cache(self, mock_boto):
        """Test secret caching"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': '{"key": "value"}'
        }
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        
        # First call
        result1 = client.get_secret('test-secret')
        # Second call should use cache
        result2 = client.get_secret('test-secret')
        
        assert result1 == result2
        assert mock_sm.get_secret_value.call_count == 1  # Only called once
    
    @patch('shared.secrets_client.boto3.client')
    def test_get_secret_no_cache(self, mock_boto):
        """Test retrieving secret without cache"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': '{"key": "value"}'
        }
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        
        result1 = client.get_secret('test-secret', use_cache=False)
        result2 = client.get_secret('test-secret', use_cache=False)
        
        assert mock_sm.get_secret_value.call_count == 2  # Called twice
    
    @patch('shared.secrets_client.boto3.client')
    def test_get_secret_not_found(self, mock_boto):
        """Test error when secret not found"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'get_secret_value'
        )
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        
        with pytest.raises(Exception, match="Secret not found"):
            client.get_secret('nonexistent-secret')
    
    @patch('shared.secrets_client.boto3.client')
    def test_get_secret_decryption_failure(self, mock_boto):
        """Test error when KMS decryption fails"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'DecryptionFailureException', 'Message': 'Decryption failed'}},
            'get_secret_value'
        )
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        
        with pytest.raises(Exception, match="Cannot decrypt secret"):
            client.get_secret('encrypted-secret')
    
    @patch('shared.secrets_client.boto3.client')
    def test_get_secret_invalid_json(self, mock_boto):
        """Test error when secret contains invalid JSON"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': 'not valid json'
        }
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        
        with pytest.raises(Exception, match="invalid JSON"):
            client.get_secret('bad-json-secret')
    
    @patch('shared.secrets_client.boto3.client')
    def test_get_database_credentials(self, mock_boto):
        """Test getting database credentials"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': '{"host": "localhost", "port": 5432, "database": "testdb"}'
        }
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        result = client.get_database_credentials()
        
        assert result['host'] == 'localhost'
        assert result['port'] == 5432
    
    @patch('shared.secrets_client.boto3.client')
    def test_get_jwt_config(self, mock_boto):
        """Test getting JWT configuration"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': '{"secret": "jwt-secret-key", "algorithm": "HS256"}'
        }
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        result = client.get_jwt_config()
        
        assert result['secret'] == 'jwt-secret-key'
        assert result['algorithm'] == 'HS256'
    
    @patch('shared.secrets_client.boto3.client')
    def test_clear_cache(self, mock_boto):
        """Test clearing the cache"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': '{"key": "value"}'
        }
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        
        # Add to cache
        client.get_secret('test-secret')
        assert len(client._cache) == 1
        
        # Clear cache
        client.clear_cache()
        assert len(client._cache) == 0
    
    @patch('shared.secrets_client.boto3.client')
    def test_health_check_success(self, mock_boto):
        """Test health check when service is available"""
        mock_sm = MagicMock()
        mock_sm.list_secrets.return_value = {'SecretList': []}
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        result = client.health_check()
        
        assert result is True
    
    @patch('shared.secrets_client.boto3.client')
    def test_health_check_failure(self, mock_boto):
        """Test health check when service is unavailable"""
        mock_sm = MagicMock()
        mock_sm.list_secrets.side_effect = Exception("Service unavailable")
        mock_boto.return_value = mock_sm
        
        client = SecretsManagerClient()
        result = client.health_check()
        
        assert result is False
