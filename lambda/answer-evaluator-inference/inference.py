from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import json

# Load model once (outside handler for reuse across invocations)
model = None

def load_model():
    global model
    if model is None:
        print("Loading model...")
        model = SentenceTransformer('/opt/ml/model/')
        print("Model loaded successfully")
    return model

def handler(event, context):
    """
    Pure ML inference - returns similarity score only
    
    Input: {
        "answer": "student's answer text",
        "correct_answer": "expected answer text"
    }
    
    Output: {
        "statusCode": 200,
        "similarity": 0.85
    }
    """
    try:
        # Direct invocation format
        answer = event.get('answer', '').strip()
        correct_answer = event.get('correct_answer', '').strip()
        
        if not answer or not correct_answer:
            return {
                'statusCode': 400,
                'error': 'Both answer and correct_answer are required'
            }
        
        # Load model
        model = load_model()
        
        # Generate embeddings
        embeddings = model.encode([answer, correct_answer])
        
        # Calculate similarity
        similarity = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
        
        return {
            'statusCode': 200,
            'similarity': similarity
        }
        
    except Exception as e:
        print(f"Inference error: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }
