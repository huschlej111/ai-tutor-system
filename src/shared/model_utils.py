"""
ONNX Model Utilities
Handles model loading, caching, and vector encoding for semantic similarity
using onnxruntime instead of sentence_transformers/torch.
"""
import os
import logging
from typing import List, Optional
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Lazy imports - only loaded when model is actually used
_ort = None
_tokenizers = None

def _get_ort():
    global _ort
    if _ort is None:
        import onnxruntime as ort
        _ort = ort
    return _ort

def _get_tokenizer_lib():
    global _tokenizers
    if _tokenizers is None:
        from transformers import AutoTokenizer
        _tokenizers = AutoTokenizer
    return _tokenizers


class ModelManager:
    """Manages the ONNX model with caching and error handling"""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.environ.get('MODEL_PATH', './final_similarity_model_onnx')
        self._session = None
        self._tokenizer = None
        self._model_loaded = False

    def load_model(self) -> bool:
        if self._model_loaded:
            return True
        try:
            onnx_path = os.path.join(self.model_path, 'model.onnx')
            if not os.path.exists(onnx_path):
                logger.error(f"ONNX model not found: {onnx_path}")
                return False

            ort = _get_ort()
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 1
            self._session = ort.InferenceSession(onnx_path, sess_options=opts)

            AutoTokenizer = _get_tokenizer_lib()
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)

            self._model_loaded = True
            logger.info("ONNX model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def _mean_pool(self, token_embeddings: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
        """Mean pooling over token embeddings, respecting attention mask."""
        mask = attention_mask[:, :, np.newaxis].astype(np.float32)
        summed = (token_embeddings * mask).sum(axis=1)
        counts = mask.sum(axis=1).clip(min=1e-9)
        return summed / counts

    def encode_text(self, text: str) -> Optional[np.ndarray]:
        return self.encode_batch([text])

    def encode_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        if not self._model_loaded and not self.load_model():
            return None
        try:
            cleaned = [' '.join(t.strip().split()) for t in texts]
            enc = self._tokenizer(cleaned, padding=True, truncation=True,
                                  max_length=128, return_tensors="np")
            outputs = self._session.run(None, {
                "input_ids": enc["input_ids"].astype(np.int64),
                "attention_mask": enc["attention_mask"].astype(np.int64),
            })
            embeddings = self._mean_pool(outputs[0], enc["attention_mask"])
            # L2 normalize
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True).clip(min=1e-9)
            return embeddings / norms
        except Exception as e:
            logger.error(f"Failed to encode: {e}")
            return None

    def calculate_similarity(self, text1: str, text2: str) -> Optional[float]:
        embeddings = self.encode_batch([text1, text2])
        if embeddings is None:
            return None
        sim = cosine_similarity(embeddings[0:1], embeddings[1:2])[0][0]
        return float(max(0.0, min(1.0, sim)))

    def calculate_batch_similarity(self, student_answers: List[str], correct_answers: List[str]) -> List[Optional[float]]:
        if len(student_answers) != len(correct_answers):
            return [None] * len(student_answers)
        all_texts = student_answers + correct_answers
        embeddings = self.encode_batch(all_texts)
        if embeddings is None:
            return [None] * len(student_answers)
        n = len(student_answers)
        results = []
        for i in range(n):
            sim = cosine_similarity(embeddings[i:i+1], embeddings[n+i:n+i+1])[0][0]
            results.append(float(max(0.0, min(1.0, sim))))
        return results

    def health_check(self) -> bool:
        try:
            sim = self.calculate_similarity("test", "test")
            return sim is not None and abs(sim - 1.0) < 0.05
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_model_info(self) -> dict:
        return {
            'loaded': self._model_loaded,
            'model_path': self.model_path,
            'backend': 'onnxruntime',
        }


_model_manager: Optional[ModelManager] = None

def get_model_manager() -> ModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager

def initialize_model() -> bool:
    return get_model_manager().load_model()

def calculate_semantic_similarity(student_answer: str, correct_answer: str) -> Optional[float]:
    return get_model_manager().calculate_similarity(student_answer, correct_answer)
