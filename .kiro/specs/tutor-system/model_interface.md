# Model Interface Documentation

## Overview

The Know-It-All Tutor system uses a custom fine-tuned sentence transformer model for intelligent answer evaluation. This model enables semantic similarity comparison between student answers and correct definitions, supporting the system's domain-agnostic architecture.

## Model Details

### Technical Specifications
- **Base Model**: DistilBERT (distilbert-base-uncased)
- **Model Type**: Sentence Transformer
- **Output Dimensions**: 768-dimensional dense vectors
- **Maximum Sequence Length**: 512 tokens
- **Similarity Function**: Cosine Similarity
- **Performance**: Spearman correlation of 0.8676 on evaluation dataset

### Model Location
- **Path**: `./final_similarity_model/`
- **Size**: ~250MB
- **Format**: Sentence Transformers compatible

## Integration Patterns

### 1. Basic Answer Evaluation

```python
from sentence_transformers import SentenceTransformer
import torch

# Load your custom model
model = SentenceTransformer('./final_similarity_model')

def evaluate_student_answer(student_answer, correct_definition, threshold=0.7):
    """
    Evaluate student answer against correct definition using similarity model
    
    Args:
        student_answer (str): The student's submitted answer
        correct_definition (str): The correct definition from knowledge domain
        threshold (float): Minimum similarity score for acceptance (0.0-1.0)
    
    Returns:
        dict: Evaluation results with score, feedback, and correctness
    """
    
    # Encode both texts to get embeddings
    embeddings = model.encode([student_answer, correct_definition])
    
    # Calculate similarity score
    similarity_score = model.similarity(embeddings, embeddings)[0][1].item()
    
    # Determine correctness based on threshold
    is_correct = similarity_score >= threshold
    
    # Generate feedback based on similarity score
    if similarity_score >= 0.9:
        feedback = "Excellent! Your answer closely matches the correct definition."
    elif similarity_score >= 0.7:
        feedback = "Good answer! Your understanding is on track with minor differences."
    elif similarity_score >= 0.5:
        feedback = "Partially correct. Your answer captures some key concepts but misses important details."
    else:
        feedback = f"Incorrect. Your answer differs significantly from the expected definition: {correct_definition}"
    
    return {
        'similarity_score': similarity_score,
        'is_correct': is_correct,
        'feedback': feedback,
        'correct_definition': correct_definition
    }
```

### 2. Quiz System Integration

```python
class QuizEvaluator:
    def __init__(self, model_path='./final_similarity_model'):
        self.model = SentenceTransformer(model_path)
        
    def evaluate_quiz_response(self, term, student_answer, knowledge_domain):
        """
        Evaluate a single quiz response within the context of a knowledge domain
        """
        # Get correct definition from knowledge domain
        correct_definition = knowledge_domain.get_definition(term)
        
        # Use similarity model for evaluation
        result = self.evaluate_student_answer(student_answer, correct_definition)
        
        # Log progress for tracking (Requirement 4)
        self.update_student_progress(term, result['similarity_score'], result['is_correct'])
        
        return result
    
    def batch_evaluate_synonyms(self, student_answer, possible_definitions):
        """
        Handle cases where multiple correct definitions exist
        """
        best_score = 0
        best_match = None
        
        for definition in possible_definitions:
            result = self.evaluate_student_answer(student_answer, definition)
            if result['similarity_score'] > best_score:
                best_score = result['similarity_score']
                best_match = result
                
        return best_match
```

### 3. AWS Lambda Deployment

```python
import json
import boto3
from sentence_transformers import SentenceTransformer

# Global model loading (outside handler for container reuse)
model = None

def lambda_handler(event, context):
    global model
    
    # Load model on cold start
    if model is None:
        # Model files should be in Lambda layer or deployment package
        model = SentenceTransformer('/opt/final_similarity_model')
    
    # Parse request
    student_answer = event['student_answer']
    correct_definition = event['correct_definition']
    threshold = event.get('threshold', 0.7)
    
    # Evaluate answer
    result = evaluate_student_answer(student_answer, correct_definition, threshold)
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

## Configuration Parameters

### Similarity Thresholds

Based on the model's performance metrics, recommended thresholds:

- **Strict evaluation**: `threshold = 0.8`
  - Use for final assessments or critical terminology
- **Moderate evaluation**: `threshold = 0.7` (default)
  - Balanced approach for general learning
- **Lenient evaluation**: `threshold = 0.6`
  - Use for initial learning phases or complex concepts

### Feedback Categories

| Similarity Score | Category | Feedback Type |
|-----------------|----------|---------------|
| 0.9 - 1.0 | Excellent | Positive reinforcement |
| 0.7 - 0.89 | Good | Encouraging with minor notes |
| 0.5 - 0.69 | Partial | Constructive guidance |
| 0.0 - 0.49 | Incorrect | Show correct definition |

## Performance Considerations

### AWS Lambda Optimization
- **Model Size**: ~250MB fits within Lambda limits
- **Cold Start**: Load model once, reuse across invocations
- **Memory**: Recommend 1GB+ for optimal performance
- **Timeout**: Set to 30+ seconds for initial cold start

### Batch Processing
```python
def batch_evaluate_answers(self, answer_pairs, threshold=0.7):
    """
    Process multiple answer evaluations in a single call
    
    Args:
        answer_pairs: List of (student_answer, correct_definition) tuples
        threshold: Similarity threshold for all evaluations
    
    Returns:
        List of evaluation results
    """
    results = []
    
    # Batch encode all texts for efficiency
    all_texts = []
    for student_answer, correct_definition in answer_pairs:
        all_texts.extend([student_answer, correct_definition])
    
    embeddings = self.model.encode(all_texts)
    
    # Process pairs
    for i, (student_answer, correct_definition) in enumerate(answer_pairs):
        student_embedding = embeddings[i*2]
        correct_embedding = embeddings[i*2 + 1]
        
        similarity_score = self.model.similarity([student_embedding], [correct_embedding])[0][0].item()
        
        result = self._generate_feedback(similarity_score, threshold, correct_definition)
        results.append(result)
    
    return results
```

### Caching Strategy
```python
import hashlib
from functools import lru_cache

class CachedQuizEvaluator(QuizEvaluator):
    def __init__(self, model_path='./final_similarity_model', cache_size=1000):
        super().__init__(model_path)
        self.definition_cache = {}
    
    @lru_cache(maxsize=1000)
    def _get_cached_embedding(self, text):
        """Cache embeddings for frequently used definitions"""
        return self.model.encode([text])[0]
    
    def evaluate_with_cache(self, student_answer, correct_definition, threshold=0.7):
        """Use cached embeddings when possible"""
        student_embedding = self._get_cached_embedding(student_answer)
        correct_embedding = self._get_cached_embedding(correct_definition)
        
        similarity_score = self.model.similarity([student_embedding], [correct_embedding])[0][0].item()
        
        return self._generate_feedback(similarity_score, threshold, correct_definition)
```

## Requirements Mapping

This model interface directly supports:

- **Requirement 7**: Answer Evaluation System
  - Intelligent comparison using semantic similarity
  - Handles synonyms and alternative phrasings
  - Provides graduated feedback based on correctness level

- **Requirement 6**: Domain-Agnostic Architecture
  - Works with any knowledge domain without code changes
  - Separates evaluation logic from content specifics

- **Requirement 4**: Progress Tracking
  - Provides numerical similarity scores for detailed analytics
  - Enables tracking of improvement over time

## Dependencies

```bash
pip install sentence-transformers torch transformers
```

For AWS Lambda deployment:
```bash
pip install sentence-transformers torch transformers -t ./lambda_package/
```

## Error Handling

```python
def safe_evaluate_answer(student_answer, correct_definition, threshold=0.7):
    """
    Wrapper with error handling for production use
    """
    try:
        if not student_answer or not student_answer.strip():
            return {
                'similarity_score': 0.0,
                'is_correct': False,
                'feedback': 'Please provide an answer.',
                'error': None
            }
        
        if not correct_definition or not correct_definition.strip():
            return {
                'similarity_score': 0.0,
                'is_correct': False,
                'feedback': 'Definition not found in knowledge domain.',
                'error': 'missing_definition'
            }
        
        return evaluate_student_answer(student_answer, correct_definition, threshold)
        
    except Exception as e:
        return {
            'similarity_score': 0.0,
            'is_correct': False,
            'feedback': 'Unable to evaluate answer. Please try again.',
            'error': str(e)
        }
```