"""
Unit tests for model_utils module
Tests ONNX model loading and encoding
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

    @patch('shared.model_utils._get_tokenizer_lib')
    @patch('shared.model_utils._get_ort')
    @patch('shared.model_utils.os.path.exists')
    def test_load_model_success(self, mock_exists, mock_get_ort, mock_get_tokenizer):
        """Test successfully loading ONNX model"""
        mock_exists.return_value = True
        mock_get_ort.return_value = MagicMock()
        mock_get_tokenizer.return_value = MagicMock()

        manager = ModelManager(model_path='/test/model')
        result = manager.load_model()

        assert result is True
        assert manager._model_loaded is True
        assert manager._session is not None

    @patch('shared.model_utils.os.path.exists')
    def test_load_model_path_not_exists(self, mock_exists):
        """Test loading model when ONNX file doesn't exist"""
        mock_exists.return_value = False

        manager = ModelManager(model_path='/nonexistent/model')
        result = manager.load_model()

        assert result is False
        assert manager._model_loaded is False

    @patch('shared.model_utils._get_tokenizer_lib')
    @patch('shared.model_utils._get_ort')
    @patch('shared.model_utils.os.path.exists')
    def test_load_model_already_loaded(self, mock_exists, mock_get_ort, mock_get_tokenizer):
        """Test that loading a second time short-circuits without reloading"""
        mock_exists.return_value = True
        mock_get_ort.return_value = MagicMock()
        mock_get_tokenizer.return_value = MagicMock()

        manager = ModelManager()
        manager.load_model()
        result = manager.load_model()  # second call

        assert result is True
        assert mock_get_ort.call_count == 1  # only loaded once

    @patch('shared.model_utils._get_ort')
    @patch('shared.model_utils.os.path.exists')
    def test_load_model_exception(self, mock_exists, mock_get_ort):
        """Test handling exception during model loading"""
        mock_exists.return_value = True
        mock_get_ort.side_effect = Exception("Model load error")

        manager = ModelManager()
        result = manager.load_model()

        assert result is False
        assert manager._session is None

    def test_encode_text_success(self):
        """Test encoding text successfully via encode_batch"""
        manager = ModelManager()
        expected = np.array([[0.1, 0.2, 0.3]])

        with patch.object(manager, 'encode_batch', return_value=expected):
            manager._model_loaded = True
            result = manager.encode_text("test text")

        assert result is not None

    @patch('shared.model_utils.os.path.exists')
    def test_encode_text_model_not_loaded(self, mock_exists):
        """Test encoding when model cannot be loaded"""
        mock_exists.return_value = False

        manager = ModelManager(model_path='/nonexistent')
        result = manager.encode_text("test text")

        assert result is None

    def test_encode_batch_success(self):
        """Test encoding multiple texts"""
        manager = ModelManager()
        manager._model_loaded = True

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            'input_ids': np.array([[1, 2], [3, 4]]),
            'attention_mask': np.array([[1, 1], [1, 0]])
        }
        manager._tokenizer = mock_tokenizer

        mock_session = MagicMock()
        mock_session.run.return_value = [np.ones((2, 2, 4))]  # [batch, seq_len, hidden_dim]
        manager._session = mock_session

        result = manager.encode_batch(["text1", "text2"])

        assert result is not None
        assert result.shape[0] == 2

    def test_calculate_similarity_success(self):
        """Test calculating similarity between texts"""
        manager = ModelManager()
        manager._model_loaded = True

        with patch.object(manager, 'encode_batch') as mock_encode:
            mock_encode.return_value = np.array([
                [1.0, 0.0, 0.0],
                [0.9, 0.1, 0.0]
            ])
            result = manager.calculate_similarity("text1", "text2")

        assert result is not None
        assert 0.0 <= result <= 1.0

    @patch('shared.model_utils.os.path.exists')
    def test_calculate_similarity_model_not_loaded(self, mock_exists):
        """Test similarity calculation when model cannot be loaded"""
        mock_exists.return_value = False

        manager = ModelManager(model_path='/nonexistent')
        result = manager.calculate_similarity("text1", "text2")

        assert result is None

    @patch('shared.model_utils._get_tokenizer_lib')
    @patch('shared.model_utils._get_ort')
    @patch('shared.model_utils.os.path.exists')
    def test_health_check_success(self, mock_exists, mock_get_ort, mock_get_tokenizer):
        """Test health check when model is loaded"""
        mock_exists.return_value = True
        mock_get_ort.return_value = MagicMock()
        mock_get_tokenizer.return_value = MagicMock()

        manager = ModelManager()
        manager.load_model()

        with patch.object(manager, 'calculate_similarity', return_value=1.0):
            result = manager.health_check()

        assert result is True

    def test_health_check_model_not_loaded(self):
        """Test health check when model not loaded"""
        manager = ModelManager(model_path='/nonexistent')
        result = manager.health_check()

        assert result is False
