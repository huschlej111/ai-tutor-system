"""
Sentence Transformer Model Utilities
Handles model loading, caching, and vector encoding for semantic similarity
"""
import os
import logging
from typing import List, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages the sentence transformer model with caching and error handling"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.environ.get('MODEL_PATH', './final_similarity_model')
        self.model: Optional[SentenceTransformer] = None
        self._model_loaded = False
    
    def load_model(self) -> bool:
        """
        Load the sentence transformer model with error handling
        Returns True if successful, False otherwise
        """
        if self._model_loaded and self.model is not None:
            return True
            
        try:
            logger.info(f"Loading sentence transformer model from {self.model_path}")
            
            # Check if model path exists
            if not os.path.exists(self.model_path):
                logger.error(f"Model path does not exist: {self.model_path}")
                return False
            
            # Load the model
            self.model = SentenceTransformer(self.model_path)
            self._model_loaded = True
            
            logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            self.model = None
            self._model_loaded = False
            return False
    
    def encode_text(self, text: str) -> Optional[np.ndarray]:
        """
        Encode text into vector representation
        Returns None if model is not loaded or encoding fails
        """
        if not self._model_loaded or self.model is None:
            if not self.load_model():
                return None
        
        try:
            # Clean and normalize text
            cleaned_text = self._clean_text(text)
            
            # Encode text to vector
            embedding = self.model.encode([cleaned_text])
            return embedding[0]  # Return single embedding
            
        except Exception as e:
            logger.error(f"Failed to encode text: {str(e)}")
            return None
    
    def encode_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Encode multiple texts into vector representations
        Returns None if model is not loaded or encoding fails
        """
        if not self._model_loaded or self.model is None:
            if not self.load_model():
                return None
        
        try:
            # Clean and normalize texts
            cleaned_texts = [self._clean_text(text) for text in texts]
            
            # Encode texts to vectors
            embeddings = self.model.encode(cleaned_texts)
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode batch: {str(e)}")
            return None
    
    def calculate_similarity(self, text1: str, text2: str) -> Optional[float]:
        """
        Calculate cosine similarity between two texts
        Returns similarity score (0.0 to 1.0) or None if calculation fails
        """
        try:
            # Encode both texts
            embedding1 = self.encode_text(text1)
            embedding2 = self.encode_text(text2)
            
            if embedding1 is None or embedding2 is None:
                return None
            
            # Calculate cosine similarity
            similarity = cosine_similarity(
                embedding1.reshape(1, -1), 
                embedding2.reshape(1, -1)
            )[0][0]
            
            # Ensure similarity is between 0 and 1
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            return None
    
    def calculate_batch_similarity(self, student_answers: List[str], correct_answers: List[str]) -> List[Optional[float]]:
        """
        Calculate similarities for multiple answer pairs
        Returns list of similarity scores or None values for failed calculations
        """
        if len(student_answers) != len(correct_answers):
            logger.error("Student answers and correct answers lists must have same length")
            return [None] * len(student_answers)
        
        try:
            # Encode all texts in batches for efficiency
            all_texts = student_answers + correct_answers
            embeddings = self.encode_batch(all_texts)
            
            if embeddings is None:
                return [None] * len(student_answers)
            
            # Split embeddings back into student and correct answer embeddings
            student_embeddings = embeddings[:len(student_answers)]
            correct_embeddings = embeddings[len(student_answers):]
            
            # Calculate similarities
            similarities = []
            for i in range(len(student_answers)):
                try:
                    similarity = cosine_similarity(
                        student_embeddings[i].reshape(1, -1),
                        correct_embeddings[i].reshape(1, -1)
                    )[0][0]
                    similarities.append(max(0.0, min(1.0, float(similarity))))
                except Exception as e:
                    logger.error(f"Failed to calculate similarity for pair {i}: {str(e)}")
                    similarities.append(None)
            
            return similarities
            
        except Exception as e:
            logger.error(f"Failed to calculate batch similarities: {str(e)}")
            return [None] * len(student_answers)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for better encoding"""
        if not text:
            return ""
        
        # Basic text cleaning
        cleaned = text.strip()
        
        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        if not self._model_loaded or self.model is None:
            return {
                'loaded': False,
                'model_path': self.model_path,
                'error': 'Model not loaded'
            }
        
        try:
            return {
                'loaded': True,
                'model_path': self.model_path,
                'max_seq_length': getattr(self.model, 'max_seq_length', 'unknown'),
                'embedding_dimension': getattr(self.model, 'get_sentence_embedding_dimension', lambda: 'unknown')()
            }
        except Exception as e:
            return {
                'loaded': True,
                'model_path': self.model_path,
                'error': f'Failed to get model info: {str(e)}'
            }
    
    def health_check(self) -> bool:
        """
        Perform a health check on the model
        Returns True if model is working correctly
        """
        try:
            # Test encoding with a simple sentence
            test_text = "This is a test sentence."
            embedding = self.encode_text(test_text)
            
            if embedding is None:
                return False
            
            # Check if embedding has expected properties
            if len(embedding.shape) != 1 or embedding.shape[0] == 0:
                return False
            
            # Test similarity calculation
            similarity = self.calculate_similarity(test_text, test_text)
            if similarity is None or abs(similarity - 1.0) > 0.01:  # Should be very close to 1.0
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


# Global model manager instance for Lambda container reuse
_model_manager: Optional[ModelManager] = None

def get_model_manager() -> ModelManager:
    """Get or create the global model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager

def initialize_model() -> bool:
    """Initialize the global model manager"""
    manager = get_model_manager()
    return manager.load_model()

def calculate_semantic_similarity(student_answer: str, correct_answer: str) -> Optional[float]:
    """Convenience function for calculating semantic similarity"""
    manager = get_model_manager()
    return manager.calculate_similarity(student_answer, correct_answer)