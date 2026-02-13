# Separation of Concerns: Lambda Handler vs ML Model Container

## Current Architecture Problem

**Issue:** Business logic (thresholds, feedback messages, API routing) is coupled with the ML model in a 2GB Docker container.

**Impact:**
- Every threshold/feedback change requires rebuilding 2GB image
- ECR push takes 5-10 minutes
- Slow iteration on business logic
- Model updates risk breaking business logic

## Current Implementation

```
lambda/answer-evaluator/
├── Dockerfile                    # 2GB container
├── lambda_function.py            # Lambda handler + business logic
├── requirements.txt
└── (model copied during build)

Changes requiring full rebuild:
- Feedback thresholds (0.85, 0.70, 0.50)
- Feedback messages
- API routing logic
- Error handling
- Logging/monitoring
```

## Proposed Architecture

### Two-Lambda Pattern

**Lambda 1: Inference Engine (Container-based)**
- Pure ML inference
- Rarely changes (only on model updates)
- Returns raw similarity scores
- 2GB container with model

**Lambda 2: Business Logic Handler (Zip-based)**
- Thresholds and feedback generation
- API routing and validation
- Integration with other services
- Fast deployment (<10 seconds)

### Directory Structure

```
lambda/answer-evaluator-inference/
├── Dockerfile                    # Model + inference only
├── inference.py                  # Pure ML code
└── requirements.txt              # ML dependencies

src/lambda_functions/answer_evaluator/
├── handler.py                    # Lambda handler (zip deployment)
├── config.py                     # Thresholds, feedback messages
└── requirements.txt              # Minimal dependencies (boto3)
```

## Implementation

### 1. Inference Lambda (Container)

**lambda/answer-evaluator-inference/inference.py:**
```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import json

model = None

def load_model():
    global model
    if model is None:
        model = SentenceTransformer('/opt/ml/model/')
    return model

def handler(event, context):
    """Pure inference - returns similarity score only"""
    try:
        # Direct invocation format
        answer = event['answer']
        correct_answer = event['correct_answer']
        
        model = load_model()
        embeddings = model.encode([answer, correct_answer])
        similarity = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
        
        return {
            'statusCode': 200,
            'similarity': similarity
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'error': str(e)
        }
```

**lambda/answer-evaluator-inference/Dockerfile:**
```dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY final_similarity_model/ /opt/ml/model/
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inference.py ${LAMBDA_TASK_ROOT}/

CMD ["inference.handler"]
```

### 2. Business Logic Lambda (Zip)

**src/lambda_functions/answer_evaluator/config.py:**
```python
import os

# Configurable thresholds (can be overridden by env vars or database)
THRESHOLDS = {
    'excellent': float(os.getenv('THRESHOLD_EXCELLENT', '0.85')),
    'good': float(os.getenv('THRESHOLD_GOOD', '0.70')),
    'partial': float(os.getenv('THRESHOLD_PARTIAL', '0.50'))
}

# Feedback messages (can be localized, personalized, etc.)
FEEDBACK_MESSAGES = {
    'excellent': "Excellent! Your answer matches the expected response.",
    'good': "Good answer, but could be more precise.",
    'partial': "Partially correct. Review the key concepts.",
    'incorrect': "Incorrect. Please review the material."
}

# Can add domain-specific overrides
DOMAIN_THRESHOLDS = {
    # 'aws-certification': {'excellent': 0.90, 'good': 0.75, 'partial': 0.55},
    # 'python-basics': {'excellent': 0.80, 'good': 0.65, 'partial': 0.45},
}
```

**src/lambda_functions/answer_evaluator/handler.py:**
```python
import boto3
import json
import os
from config import THRESHOLDS, FEEDBACK_MESSAGES, DOMAIN_THRESHOLDS

lambda_client = boto3.client('lambda')
INFERENCE_FUNCTION_NAME = os.environ['INFERENCE_FUNCTION_NAME']

def generate_feedback(similarity: float, domain_id: str = None) -> str:
    """Generate feedback based on similarity score and optional domain"""
    thresholds = DOMAIN_THRESHOLDS.get(domain_id, THRESHOLDS)
    
    if similarity >= thresholds['excellent']:
        return FEEDBACK_MESSAGES['excellent']
    elif similarity >= thresholds['good']:
        return FEEDBACK_MESSAGES['good']
    elif similarity >= thresholds['partial']:
        return FEEDBACK_MESSAGES['partial']
    else:
        return FEEDBACK_MESSAGES['incorrect']

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
        
        if http_method == 'GET' and '/health' in path:
            return handle_health_check()
        
        body = event
        if 'body' in event:
            if isinstance(event['body'], str) and event['body']:
                body = json.loads(event['body'])
            elif event['body']:
                body = event['body']
        
        if '/batch' in path or body.get('batch'):
            return handle_batch_evaluation(body)
        
        return handle_single_evaluation(body)
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_single_evaluation(body):
    """Handle single answer evaluation"""
    answer = body.get('answer', '').strip()
    correct_answer = body.get('correct_answer', '').strip()
    domain_id = body.get('domain_id')  # Optional domain-specific thresholds
    
    if not answer or not correct_answer:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Both answer and correct_answer are required'})
        }
    
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
    
    if result['statusCode'] != 200:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Inference failed'})
        }
    
    similarity = result['similarity']
    feedback = generate_feedback(similarity, domain_id)
    
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
    """Handle batch evaluation - can optimize with parallel invocations"""
    answer_pairs = body.get('answer_pairs', [])
    domain_id = body.get('domain_id')
    
    if not answer_pairs or not isinstance(answer_pairs, list):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'answer_pairs array is required'})
        }
    
    results = []
    for pair in answer_pairs:
        if not isinstance(pair, dict) or 'answer' not in pair or 'correct_answer' not in pair:
            results.append({'error': True, 'message': 'Invalid pair format'})
            continue
        
        # Invoke inference Lambda
        response = lambda_client.invoke(
            FunctionName=INFERENCE_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'answer': pair['answer'].strip(),
                'correct_answer': pair['correct_answer'].strip()
            })
        )
        
        result = json.loads(response['Payload'].read())
        
        if result['statusCode'] == 200:
            similarity = result['similarity']
            feedback = generate_feedback(similarity, domain_id)
            results.append({
                'similarity': round(similarity, 4),
                'feedback': feedback,
                'error': False
            })
        else:
            results.append({'error': True, 'message': 'Inference failed'})
    
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

def handle_health_check():
    """Health check - verifies inference Lambda is accessible"""
    try:
        response = lambda_client.invoke(
            FunctionName=INFERENCE_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'answer': 'test',
                'correct_answer': 'test'
            })
        )
        result = json.loads(response['Payload'].read())
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'healthy',
                'inference_available': result['statusCode'] == 200,
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
```

### 3. CDK Stack Changes

**infrastructure/stacks/auth_only_stack.py:**
```python
# Inference Lambda (Container-based)
inference_repo = ecr.Repository.from_repository_name(
    self, "InferenceRepo",
    repository_name="answer-evaluator-inference"
)

self.inference_lambda = _lambda.DockerImageFunction(
    self, "InferenceFunction",
    code=_lambda.DockerImageCode.from_ecr(
        repository=inference_repo,
        tag_or_digest="latest"
    ),
    timeout=Duration.seconds(120),
    memory_size=2048,
    description="ML Inference - Semantic similarity calculation"
)

# Business Logic Lambda (Zip-based)
self.answer_evaluator_lambda = _lambda.Function(
    self, "AnswerEvaluatorFunction",
    runtime=_lambda.Runtime.PYTHON_3_12,
    handler="handler.lambda_handler",
    code=_lambda.Code.from_asset("../src/lambda_functions/answer_evaluator"),
    timeout=Duration.seconds(30),
    memory_size=256,
    layers=[self.shared_layer],
    environment={
        "INFERENCE_FUNCTION_NAME": self.inference_lambda.function_name,
        "THRESHOLD_EXCELLENT": "0.85",
        "THRESHOLD_GOOD": "0.70",
        "THRESHOLD_PARTIAL": "0.50",
        "LOG_LEVEL": "INFO"
    },
    description="Answer Evaluator - Business logic and API routing"
)

# Grant permission to invoke inference Lambda
self.inference_lambda.grant_invoke(self.answer_evaluator_lambda)
```

## Benefits

### Development Velocity
- **Threshold changes**: Update env vars or config.py, deploy in 10 seconds
- **Feedback messages**: Edit config.py, deploy in 10 seconds
- **API changes**: Modify handler.py, deploy in 10 seconds
- **Model updates**: Rebuild container only when model changes

### Flexibility
- Domain-specific thresholds without code changes
- A/B testing different feedback strategies
- Localization support
- Personalized feedback based on user history

### Cost
- Extra Lambda invocation: ~$0.0000002 per evaluation
- Negligible compared to development time savings

### Operational
- Independent scaling (inference can have higher concurrency)
- Separate monitoring and logging
- Easier rollback (business logic vs model)
- Can cache inference results if needed

## Migration Path

1. **Phase 1**: Deploy inference Lambda alongside current implementation
2. **Phase 2**: Create new business logic Lambda, test in parallel
3. **Phase 3**: Update API Gateway to route to new handler
4. **Phase 4**: Deprecate old monolithic Lambda
5. **Phase 5**: Extract thresholds to DynamoDB for dynamic configuration

## Future Enhancements

- **Dynamic thresholds**: Store in DynamoDB, update without deployment
- **Caching layer**: Cache inference results for identical answer pairs
- **Batch optimization**: Parallel Lambda invocations for batch requests
- **Monitoring**: Separate CloudWatch metrics for inference vs business logic
- **Multi-model support**: Route to different inference Lambdas by domain

## Decision

**Recommendation**: Implement two-Lambda pattern before production launch.

**Rationale**: 
- Current architecture couples fast-changing business logic with slow-to-deploy container
- Feedback thresholds will need tuning based on user testing
- Domain-specific customization is likely requirement
- Cost is negligible, benefits are significant

**When to implement**: Before adding more domains or launching to users who will provide feedback requiring threshold adjustments.
