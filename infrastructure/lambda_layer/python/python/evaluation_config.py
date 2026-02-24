"""
Configuration for Answer Evaluation Service
Defines thresholds, feedback templates, and evaluation settings
"""
import os
from typing import Dict, Any
from enum import Enum

class EvaluationMode(Enum):
    """Evaluation modes with different threshold settings"""
    STRICT = "strict"      # 0.8 threshold - for final assessments
    MODERATE = "moderate"  # 0.7 threshold - default, balanced approach
    LENIENT = "lenient"    # 0.6 threshold - for initial learning phases

class EvaluationConfig:
    """Configuration class for answer evaluation settings"""
    
    # Default thresholds for different evaluation modes
    THRESHOLDS = {
        EvaluationMode.STRICT: 0.8,
        EvaluationMode.MODERATE: 0.7,
        EvaluationMode.LENIENT: 0.6
    }
    
    # Feedback score ranges
    EXCELLENT_THRESHOLD = 0.9
    GOOD_THRESHOLD = 0.8
    CLOSE_RANGE = 0.1  # Within 0.1 of threshold is considered "close"
    PARTIAL_THRESHOLD = 0.3
    
    # Model configuration
    DEFAULT_MODEL_PATH = './final_similarity_model'
    MAX_BATCH_SIZE = 100
    MAX_TEXT_LENGTH = 1000  # Characters
    
    # Performance settings
    SIMILARITY_PRECISION = 4  # Decimal places for similarity scores
    
    @classmethod
    def get_threshold(cls, mode: str = "moderate") -> float:
        """Get threshold for evaluation mode"""
        try:
            eval_mode = EvaluationMode(mode.lower())
            return cls.THRESHOLDS[eval_mode]
        except ValueError:
            return cls.THRESHOLDS[EvaluationMode.MODERATE]
    
    @classmethod
    def get_model_path(cls) -> str:
        """Get model path from environment or default"""
        return os.environ.get('MODEL_PATH', cls.DEFAULT_MODEL_PATH)
    
    @classmethod
    def validate_threshold(cls, threshold: float) -> bool:
        """Validate that threshold is in acceptable range"""
        return 0.0 <= threshold <= 1.0
    
    @classmethod
    def validate_text_length(cls, text: str) -> bool:
        """Validate that text is not too long"""
        return len(text) <= cls.MAX_TEXT_LENGTH
    
    @classmethod
    def get_feedback_template(cls, similarity_score: float, threshold: float) -> str:
        """Get appropriate feedback template based on score"""
        if similarity_score >= cls.EXCELLENT_THRESHOLD:
            return "excellent"
        elif similarity_score >= threshold:
            if similarity_score >= cls.GOOD_THRESHOLD:
                return "good"
            else:
                return "correct"
        elif similarity_score >= (threshold - cls.CLOSE_RANGE):
            return "close"
        elif similarity_score >= cls.PARTIAL_THRESHOLD:
            return "partial"
        else:
            return "incorrect"

class FeedbackTemplates:
    """Templates for generating feedback messages"""
    
    TEMPLATES = {
        "excellent": "Excellent! Your answer demonstrates a clear and comprehensive understanding of the concept.",
        "good": "Great job! Your answer is correct and shows good understanding.",
        "correct": "Good work! Your answer is correct, though it could be more detailed.",
        "close": "Close! Your answer shows some understanding, but could be more precise. The correct answer is: {correct_answer}",
        "partial": "Partially correct. Your answer touches on some key points, but misses important details. The correct answer is: {correct_answer}",
        "incorrect": "Not quite right. Let's review this concept. The correct answer is: {correct_answer}"
    }
    
    @classmethod
    def get_feedback(cls, template_key: str, correct_answer: str = "") -> str:
        """Get feedback message from template"""
        template = cls.TEMPLATES.get(template_key, cls.TEMPLATES["incorrect"])
        return template.format(correct_answer=correct_answer.strip())

# Environment-specific configurations
def get_evaluation_config() -> Dict[str, Any]:
    """Get evaluation configuration based on environment"""
    env = os.environ.get('ENVIRONMENT', 'development')
    
    base_config = {
        'model_path': EvaluationConfig.get_model_path(),
        'max_batch_size': EvaluationConfig.MAX_BATCH_SIZE,
        'max_text_length': EvaluationConfig.MAX_TEXT_LENGTH,
        'similarity_precision': EvaluationConfig.SIMILARITY_PRECISION
    }
    
    if env == 'production':
        base_config.update({
            'default_threshold': EvaluationConfig.get_threshold('moderate'),
            'enable_caching': True,
            'log_level': 'INFO'
        })
    elif env == 'staging':
        base_config.update({
            'default_threshold': EvaluationConfig.get_threshold('moderate'),
            'enable_caching': True,
            'log_level': 'DEBUG'
        })
    else:  # development/local
        base_config.update({
            'default_threshold': EvaluationConfig.get_threshold('lenient'),
            'enable_caching': False,
            'log_level': 'DEBUG'
        })
    
    return base_config