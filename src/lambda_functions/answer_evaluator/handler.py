"""
Answer Evaluator Business Logic Lambda
Handles API routing, validation, and feedback generation
Invokes inference Lambda for ML predictions
"""
import boto3
import json
import os
import logging
from config import generate_feedback

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Initialize Lambda client
lambda_client = boto3.client('lambda')
INFERENCE_FUNCTION_NAME = os.environ.get('INFERENCE_FUNCTION_NAME')

def lambda_handler(event, context):
    """
    Business logic handler - routes requests and applies thresholds
    
    Routes:
    - POST /quiz/evaluate - Single answer evaluation
    - POST /quiz/evaluate/batch - Batch evaluation
    - GET /quiz/evaluate/health - Health check
    """
    try:
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        
        logger.info(f"Request: {http_method} {path}")
        
        # Health check endpoint
        if http_method == 'GET' and '/health' in path:
            return handle_health_check()
        
        # Parse body
        body = event
        if 'body' in event:
            if isinstance(event['body'], str) and event['body']:
                body = json.loads(event['body'])
            elif event['body']:
                body = event['body']
        
        # Route to appropriate handler
        if '/batch' in path or body.get('batch'):
            return handle_batch_evaluation(body)
        
        return handle_single_evaluation(body)
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }


def handle_single_evaluation(body):
    """Handle single answer evaluation"""
    try:
        answer = body.get('answer', '').strip()
        correct_answer = body.get('correct_answer', '').strip()
        domain_id = body.get('domain_id')  # Optional domain-specific thresholds
        
        if not answer or not correct_answer:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Both answer and correct_answer are required'})
            }
        
        logger.info(f"Evaluating answer (domain: {domain_id})")
        
        # Invoke inference Lambda
        response = lambda_client.invoke(
            FunctionName=INFERENCE_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'answer': answer,
                'correct_answer': correct_answer
            })
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') != 200:
            logger.error(f"Inference failed: {result}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Inference failed', 'details': result.get('error')})
            }
        
        similarity = result['similarity']
        feedback = generate_feedback(similarity, domain_id)
        
        logger.info(f"Evaluation complete: similarity={similarity:.4f}")
        
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
        
    except Exception as e:
        logger.error(f"Single evaluation error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_batch_evaluation(body):
    """Handle batch evaluation - processes multiple answer pairs"""
    try:
        answer_pairs = body.get('answer_pairs', [])
        domain_id = body.get('domain_id')
        
        if not answer_pairs or not isinstance(answer_pairs, list):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'answer_pairs array is required'})
            }
        
        logger.info(f"Batch evaluation: {len(answer_pairs)} pairs")
        
        results = []
        for i, pair in enumerate(answer_pairs):
            if not isinstance(pair, dict) or 'answer' not in pair or 'correct_answer' not in pair:
                results.append({
                    'error': True,
                    'message': f'Invalid pair format at index {i}'
                })
                continue
            
            # Invoke inference Lambda
            try:
                response = lambda_client.invoke(
                    FunctionName=INFERENCE_FUNCTION_NAME,
                    InvocationType='RequestResponse',
                    Payload=json.dumps({
                        'answer': pair['answer'].strip(),
                        'correct_answer': pair['correct_answer'].strip()
                    })
                )
                
                result = json.loads(response['Payload'].read())
                
                if result.get('statusCode') == 200:
                    similarity = result['similarity']
                    feedback = generate_feedback(similarity, domain_id)
                    results.append({
                        'similarity': round(similarity, 4),
                        'feedback': feedback,
                        'error': False
                    })
                else:
                    results.append({
                        'error': True,
                        'message': 'Inference failed'
                    })
            except Exception as e:
                logger.error(f"Batch item {i} error: {e}")
                results.append({
                    'error': True,
                    'message': str(e)
                })
        
        logger.info(f"Batch evaluation complete: {len(results)} results")
        
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
        
    except Exception as e:
        logger.error(f"Batch evaluation error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_health_check():
    """Health check - verifies inference Lambda is accessible"""
    try:
        logger.info("Health check requested")
        
        # Test inference Lambda with simple request
        response = lambda_client.invoke(
            FunctionName=INFERENCE_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'answer': 'test',
                'correct_answer': 'test'
            })
        )
        
        result = json.loads(response['Payload'].read())
        inference_healthy = result.get('statusCode') == 200
        
        logger.info(f"Health check: inference_healthy={inference_healthy}")
        
        return {
            'statusCode': 200 if inference_healthy else 503,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'healthy' if inference_healthy else 'unhealthy',
                'inference_available': inference_healthy,
                'inference_function': INFERENCE_FUNCTION_NAME,
                'message': 'Answer Evaluator is ready' if inference_healthy else 'Inference Lambda unavailable'
            })
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
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
