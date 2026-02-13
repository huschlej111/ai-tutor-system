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
    Evaluate semantic similarity between student answer and correct answer
    Supports single evaluation, batch evaluation, and health check
    
    Routes:
    - POST /quiz/evaluate - Single answer evaluation
    - POST /quiz/evaluate/batch - Batch answer evaluation
    - GET /quiz/evaluate/health - Health check
    """
    try:
        # Determine route from path
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        
        # Health check endpoint
        if http_method == 'GET' and '/health' in path:
            return handle_health_check()
        
        # Parse input (handle both API Gateway and direct invocation)
        body = event
        if 'body' in event:
            if isinstance(event['body'], str) and event['body']:
                body = json.loads(event['body'])
            elif event['body']:
                body = event['body']
        
        # Batch evaluation endpoint
        if '/batch' in path or body.get('batch'):
            return handle_batch_evaluation(body)
        
        # Single evaluation (default)
        return handle_single_evaluation(body)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_health_check():
    """Health check endpoint - verifies model is loaded"""
    try:
        model = load_model()
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'healthy',
                'model_loaded': model is not None,
                'message': 'Answer Evaluator is ready'
            })
        }
    except Exception as e:
        return {
            'statusCode': 503,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'unhealthy',
                'error': str(e)
            })
        }


def handle_single_evaluation(body):
    """Handle single answer evaluation"""
    answer = body.get('answer', '').strip()
    correct_answer = body.get('correct_answer', '').strip()
    
    if not answer or not correct_answer:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Both answer and correct_answer are required'})
        }
    
    # Load model
    model = load_model()
    
    # Generate embeddings
    embeddings = model.encode([answer, correct_answer])
    
    # Calculate similarity
    similarity = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
    
    # Generate feedback based on similarity score
    if similarity >= 0.85:
        feedback = "Excellent! Your answer matches the expected response."
    elif similarity >= 0.70:
        feedback = "Good answer, but could be more precise."
    elif similarity >= 0.50:
        feedback = "Partially correct. Review the key concepts."
    else:
        feedback = "Incorrect. Please review the material."
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'similarity': round(similarity, 4),
            'feedback': feedback
        })
    }


def handle_batch_evaluation(body):
    """Handle batch answer evaluation"""
    answer_pairs = body.get('answer_pairs', [])
    
    if not answer_pairs or not isinstance(answer_pairs, list):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'answer_pairs array is required'})
        }
    
    # Validate input
    for i, pair in enumerate(answer_pairs):
        if not isinstance(pair, dict) or 'answer' not in pair or 'correct_answer' not in pair:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid answer pair at index {i}'})
            }
    
    # Load model
    model = load_model()
    
    # Process all pairs
    results = []
    for pair in answer_pairs:
        answer = pair['answer'].strip()
        correct_answer = pair['correct_answer'].strip()
        
        if not answer or not correct_answer:
            results.append({
                'similarity': 0.0,
                'feedback': 'Empty answer or correct_answer',
                'error': True
            })
            continue
        
        # Generate embeddings
        embeddings = model.encode([answer, correct_answer])
        
        # Calculate similarity
        similarity = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
        
        # Generate feedback
        if similarity >= 0.85:
            feedback = "Excellent! Your answer matches the expected response."
        elif similarity >= 0.70:
            feedback = "Good answer, but could be more precise."
        elif similarity >= 0.50:
            feedback = "Partially correct. Review the key concepts."
        else:
            feedback = "Incorrect. Please review the material."
        
        results.append({
            'similarity': round(similarity, 4),
            'feedback': feedback,
            'error': False
        })
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'results': results,
            'total_evaluated': len(results)
        })
    }

