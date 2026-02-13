"""
Unit tests for config module
Tests configuration management
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.mark.unit
class TestConfig:
    """Test configuration management"""
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'test', 'AWS_REGION': 'us-east-1'})
    def test_get_environment(self):
        """Test getting environment variable"""
        from shared.config import get_config
        
        config = get_config()
        assert config.environment == 'test'
    
    @patch.dict(os.environ, {'AWS_REGION': 'us-west-2'})
    def test_get_region(self):
        """Test getting AWS region"""
        from shared.config import get_config
        
        config = get_config()
        assert config.region == 'us-west-2'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_default_environment(self):
        """Test default environment when not set"""
        from shared.config import get_config
        
        config = get_config()
        assert config.environment in ['local', 'development']
    
    def test_config_singleton(self):
        """Test config is singleton"""
        from shared.config import get_config
        
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
