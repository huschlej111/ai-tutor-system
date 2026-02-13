"""
Unit tests for model_utils module
Tests ML model loading and encoding
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.model_utils import ModelManager


@pytest.mark.unit
class TestModelManager:
    """Test ModelManager class"""
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_load_model_success(self, mock_exists, mock_transformer):
        """Test successfully loading model"""
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        manager = ModelManager(model_path='/test/model')
        result = manager.load_model()
        
        assert result is True
        assert manager._model_loaded is True
        assert manager.model is not None
    
    @patch('shared.model_utils.os.path.exists')
    def test_load_model_path_not_exists(self, mock_exists):
        """Test loading model when path doesn't exist"""
        mock_exists.return_value = False
        
        manager = ModelManager(model_path='/nonexistent/model')
        result = manager.load_model()
        
        assert result is False
        assert manager._model_loaded is False
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_load_model_already_loaded(self, mock_exists, mock_transformer):
        """Test loading model when already loaded"""
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        manager = ModelManager()
        manager.load_model()
        
        # Load again - should return True without reloading
        result = manager.load_model()
        assert result is True
        assert mock_transformer.call_count == 1  # Only called once
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_load_model_exception(self, mock_exists, mock_transformer):
        """Test handling exception during model loading"""
        mock_exists.return_value = True
        mock_transformer.side_effect = Exception("Model load error")
        
        manager = ModelManager()
        result = manager.load_model()
        
        assert result is False
        assert manager.model is None
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_encode_text_success(self, mock_exists, mock_transformer):
        """Test encoding text successfully"""
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_transformer.return_value = mock_model
        
        manager = ModelManager()
        manager.load_model()
        
        result = manager.encode_text("test text")
        
        assert result is not None
        assert len(result) == 3
        assert result[0] == 0.1
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_encode_text_model_not_loaded(self, mock_exists, mock_transformer):
        """Test encoding when model not loaded"""
        mock_exists.return_value = False
        
        manager = ModelManager()
        result = manager.encode_text("test text")
        
        assert result is None
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_encode_batch_success(self, mock_exists, mock_transformer):
        """Test encoding multiple texts"""
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_transformer.return_value = mock_model
        
        manager = ModelManager()
        manager.load_model()
        
        result = manager.encode_batch(["text1", "text2"])
        
        assert result is not None
        assert result.shape == (2, 2)
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_calculate_similarity_success(self, mock_exists, mock_transformer):
        """Test calculating similarity between texts"""
        mock_exists.return_value = True
        mock_model = MagicMock()
        # Return similar vectors
        mock_model.encode.return_value = np.array([[1.0, 0.0, 0.0]])
        mock_transformer.return_value = mock_model
        
        manager = ModelManager()
        manager.load_model()
        
        # Mock encode_text to return vectors
        with patch.object(manager, 'encode_text') as mock_encode:
            mock_encode.side_effect = [
                np.array([1.0, 0.0, 0.0]),
                np.array([0.9, 0.1, 0.0])
            ]
            
            result = manager.calculate_similarity("text1", "text2")
            
            assert result is not None
            assert 0.0 <= result <= 1.0
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_calculate_similarity_model_not_loaded(self, mock_exists, mock_transformer):
        """Test similarity calculation when model not loaded"""
        mock_exists.return_value = False
        
        manager = ModelManager()
        result = manager.calculate_similarity("text1", "text2")
        
        assert result is None
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_health_check_success(self, mock_exists, mock_transformer):
        """Test health check when model is loaded"""
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2]])
        mock_transformer.return_value = mock_model
        
        manager = ModelManager()
        manager.load_model()
        
        result = manager.health_check()
        
        assert result is True
    
    def test_health_check_model_not_loaded(self):
        """Test health check when model not loaded"""
        manager = ModelManager(model_path='/nonexistent')
        result = manager.health_check()
        
        assert result is False
    
    @patch('shared.model_utils.SentenceTransformer')
    @patch('shared.model_utils.os.path.exists')
    def test_clean_text(self, mock_exists, mock_transformer):
        """Test text cleaning"""
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        manager = ModelManager()
        manager.load_model()
        
        # Test with whitespace and special characters
        cleaned = manager._clean_text("  Test   text\n\t  ")
        assert cleaned == "Test text"
