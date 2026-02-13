#!/usr/bin/env python3
"""
Comprehensive Test Script for Quiz Engine Lambda
Tests all quiz operations without API Gateway integration
"""
import boto3
import json
import sys
import time
from typing import Dict, Any

# AWS Configuration
REGION = 'us-east-1'
QUIZ_ENGINE_FUNCTION = 'TutorSystemStack-dev-QuizEngineFunction6E7FA38A-gfMfQxsSrgIx'
DB_PROXY_FUNCTION = 'TutorSystemStack-dev-DBProxyFunction9188AB04-FbVKref3emug'

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=REGION)

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.RESET}")


def invoke_quiz_engine(event: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke Quiz Engine Lambda"""
    try:
        response = lambda_client.invoke(
            FunctionName=QUIZ_ENGINE_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        return result
    except Exception as e:
        print_error(f"Lambda invocation failed: {e}")
        return None


def invoke_db_proxy(query: str, params: list = None, return_dict: bool = True) -> Any:
    """Invoke DB Proxy Lambda"""
    try:
        payload = {
            'operation': 'execute_query',
            'query': query,
            'return_dict': return_dict
        }
        if params:
            payload['params'] = params
        
        response = lambda_client.invoke(
            FunctionName=DB_PROXY_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        body = json.loads(result['body'])
        return body.get('result')
    except Exception as e:
        print_error(f"DB Proxy invocation failed: {e}")
        return None


def get_test_data():
    """Get test user and domain data"""
    print_header("Phase 1: Getting Test Data")
    
    # Get user
    users = invoke_db_proxy(
        "SELECT id, cognito_sub, email FROM users LIMIT 1"
    )
    
    if not users:
        print_error("No users found in database")
        return None
    
    user = users[0]
    print_success(f"Found user: {user['email']} (ID: {user['id']})")
    
    # Get domain with terms
    domains = invoke_db_proxy("""
        SELECT d.id, d.data->>'name' as name, d.user_id,
               COUNT(t.id) as term_count
        FROM tree_nodes d
        LEFT JOIN tree_nodes t ON t.parent_id = d.id AND t.node_type = 'term'
        WHERE d.node_type = 'domain' AND d.user_id = %s
        GROUP BY d.id, d.data, d.user_id
        HAVING COUNT(t.id) > 0
        LIMIT 1
    """, [user['id']])
    
    if not domains:
        print_error("No domains with terms found")
        return None
    
    domain = domains[0]
    print_success(f"Found domain: {domain['name']} ({domain['term_count']} terms)")
    
    return {
        'user_id': user['id'],
        'cognito_sub': user['cognito_sub'],
        'email': user['email'],
        'domain_id': domain['id'],
        'domain_name': domain['name'],
        'term_count': domain['term_count']
    }


def test_start_quiz(test_data: Dict) -> str:
    """Test 1: Start Quiz"""
    print_header("Test 1: Start Quiz")
    
    event = {
        'httpMethod': 'POST',
        'path': '/quiz/start',
        'body': json.dumps({'domain_id': test_data['domain_id']}),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': test_data['cognito_sub'],
                    'email': test_data['email']
                }
            }
        }
    }
    
    print_info(f"Starting quiz for domain: {test_data['domain_name']}")
    response = invoke_quiz_engine(event)
    
    if not response:
        print_error("Failed to invoke Lambda")
        return None
    
    if response.get('statusCode') != 200:
        print_error(f"Quiz start failed: {response.get('body')}")
        return None
    
    body = json.loads(response['body'])
    session_id = body.get('session_id')
    current_question = body.get('current_question')
    
    print_success(f"Quiz started successfully!")
    print_info(f"  Session ID: {session_id}")
    print_info(f"  Status: {body.get('status')}")
    print_info(f"  Total Questions: {body.get('progress', {}).get('total_questions')}")
    
    if current_question:
        print_info(f"  First Question: {current_question.get('term')}")
        print_info(f"  Question {current_question.get('question_number')}/{current_question.get('total_questions')}")
    
    return session_id


def verify_session_in_db(session_id: str):
    """Verify quiz session was created in database"""
    print_header("Test 2: Verify Session in Database")
    
    sessions = invoke_db_proxy(
        "SELECT id, status, current_term_index, total_questions FROM quiz_sessions WHERE id = %s",
        [session_id]
    )
    
    if not sessions:
        print_error("Session not found in database")
        return False
    
    session = sessions[0]
    print_success("Session found in database!")
    print_info(f"  Status: {session['status']}")
    print_info(f"  Current Index: {session['current_term_index']}")
    print_info(f"  Total Questions: {session['total_questions']}")
    
    return True


def test_get_next_question(session_id: str, test_data: Dict):
    """Test 3: Get Next Question"""
    print_header("Test 3: Get Next Question")
    
    event = {
        'httpMethod': 'GET',
        'path': '/quiz/question',
        'queryStringParameters': {'session_id': session_id},
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': test_data['cognito_sub'],
                    'email': test_data['email']
                }
            }
        }
    }
    
    response = invoke_quiz_engine(event)
    
    if not response or response.get('statusCode') != 200:
        print_error(f"Failed to get question: {response.get('body') if response else 'No response'}")
        return None
    
    body = json.loads(response['body'])
    question = body.get('current_question')
    
    if question:
        print_success("Question retrieved successfully!")
        print_info(f"  Term: {question.get('term')}")
        print_info(f"  Question {question.get('question_number')}/{question.get('total_questions')}")
        print_info(f"  Term ID: {question.get('term_id')}")
        return question
    else:
        print_error("No question in response")
        return None


def test_submit_answer(session_id: str, term_id: str, test_data: Dict):
    """Test 4: Submit Answer"""
    print_header("Test 4: Submit Answer")
    
    # Get the correct answer first
    terms = invoke_db_proxy(
        "SELECT data->>'definition' as definition FROM tree_nodes WHERE id = %s",
        [term_id]
    )
    
    if not terms:
        print_error("Could not get term definition")
        return False
    
    correct_answer = terms[0]['definition']
    print_info(f"Correct answer: {correct_answer[:50]}...")
    
    # Submit a similar answer
    student_answer = correct_answer[:30] + "..."  # Partial answer
    
    event = {
        'httpMethod': 'POST',
        'path': '/quiz/answer',
        'body': json.dumps({
            'session_id': session_id,
            'answer': student_answer
        }),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': test_data['cognito_sub'],
                    'email': test_data['email']
                }
            }
        }
    }
    
    print_info(f"Submitting answer: {student_answer[:50]}...")
    response = invoke_quiz_engine(event)
    
    if not response or response.get('statusCode') != 200:
        print_error(f"Failed to submit answer: {response.get('body') if response else 'No response'}")
        return False
    
    body = json.loads(response['body'])
    evaluation = body.get('evaluation', {})
    
    print_success("Answer submitted successfully!")
    print_info(f"  Is Correct: {evaluation.get('is_correct')}")
    print_info(f"  Similarity Score: {evaluation.get('similarity_score')}")
    print_info(f"  Feedback: {evaluation.get('feedback')}")
    
    # Check if Answer Evaluator was invoked
    if 'similarity_score' in evaluation:
        print_success("Answer Evaluator integration working!")
    
    return True


def verify_progress_in_db(session_id: str):
    """Verify progress was recorded in database"""
    print_header("Test 5: Verify Progress in Database")
    
    progress = invoke_db_proxy(
        "SELECT id, is_correct, similarity_score, feedback FROM progress_records WHERE session_id = %s",
        [session_id]
    )
    
    if not progress:
        print_error("No progress records found")
        return False
    
    print_success(f"Found {len(progress)} progress record(s)!")
    for i, record in enumerate(progress, 1):
        print_info(f"  Record {i}:")
        print_info(f"    Correct: {record['is_correct']}")
        print_info(f"    Similarity: {record['similarity_score']}")
        print_info(f"    Feedback: {record['feedback'][:50]}...")
    
    return True


def test_pause_quiz(session_id: str, test_data: Dict):
    """Test 6: Pause Quiz"""
    print_header("Test 6: Pause Quiz")
    
    event = {
        'httpMethod': 'POST',
        'path': '/quiz/pause',
        'body': json.dumps({'session_id': session_id}),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': test_data['cognito_sub'],
                    'email': test_data['email']
                }
            }
        }
    }
    
    response = invoke_quiz_engine(event)
    
    if not response or response.get('statusCode') != 200:
        print_error(f"Failed to pause quiz: {response.get('body') if response else 'No response'}")
        return False
    
    body = json.loads(response['body'])
    print_success("Quiz paused successfully!")
    print_info(f"  Status: {body.get('status')}")
    
    # Verify in database
    sessions = invoke_db_proxy(
        "SELECT status, paused_at FROM quiz_sessions WHERE id = %s",
        [session_id]
    )
    
    if sessions and sessions[0]['status'] == 'paused':
        print_success("Status verified in database: paused")
        return True
    else:
        print_error("Status not updated in database")
        return False


def test_resume_quiz(session_id: str, test_data: Dict):
    """Test 7: Resume Quiz"""
    print_header("Test 7: Resume Quiz")
    
    event = {
        'httpMethod': 'POST',
        'path': '/quiz/resume',
        'body': json.dumps({'session_id': session_id}),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': test_data['cognito_sub'],
                    'email': test_data['email']
                }
            }
        }
    }
    
    response = invoke_quiz_engine(event)
    
    if not response or response.get('statusCode') != 200:
        print_error(f"Failed to resume quiz: {response.get('body') if response else 'No response'}")
        return False
    
    body = json.loads(response['body'])
    print_success("Quiz resumed successfully!")
    print_info(f"  Status: {body.get('status')}")
    
    current_question = body.get('current_question')
    if current_question:
        print_info(f"  Current Question: {current_question.get('term')}")
    
    # Verify in database
    sessions = invoke_db_proxy(
        "SELECT status FROM quiz_sessions WHERE id = %s",
        [session_id]
    )
    
    if sessions and sessions[0]['status'] == 'active':
        print_success("Status verified in database: active")
        return True
    else:
        print_error("Status not updated in database")
        return False


def check_cloudwatch_logs():
    """Check CloudWatch logs for session state transitions"""
    print_header("Test 8: Validate CloudWatch Logs")
    
    logs_client = boto3.client('logs', region_name=REGION)
    log_group = f'/aws/lambda/{QUIZ_ENGINE_FUNCTION}'
    
    try:
        # Get recent log streams
        streams = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if not streams['logStreams']:
            print_error("No log streams found")
            return False
        
        latest_stream = streams['logStreams'][0]
        print_success(f"Found log stream: {latest_stream['logStreamName']}")
        
        # Get recent events
        events = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=latest_stream['logStreamName'],
            limit=20,
            startFromHead=False
        )
        
        if events['events']:
            print_success(f"Retrieved {len(events['events'])} log events")
            print_info("Recent log messages:")
            for event in events['events'][-5:]:
                message = event['message'].strip()
                if len(message) > 100:
                    message = message[:100] + "..."
                print_info(f"  {message}")
            return True
        else:
            print_error("No log events found")
            return False
            
    except Exception as e:
        print_error(f"Failed to check CloudWatch logs: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║   Quiz Engine Lambda - Comprehensive Test Suite                   ║")
    print("║   Testing without API Gateway Integration                         ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    results = {}
    
    # Get test data
    test_data = get_test_data()
    if not test_data:
        print_error("Failed to get test data")
        return False
    
    # Test 1: Start Quiz
    session_id = test_start_quiz(test_data)
    results['start_quiz'] = session_id is not None
    
    if not session_id:
        print_error("Cannot continue without session ID")
        return False
    
    # Test 2: Verify Session in DB
    results['verify_session'] = verify_session_in_db(session_id)
    
    # Test 3: Get Next Question
    question = test_get_next_question(session_id, test_data)
    results['get_question'] = question is not None
    
    if question:
        # Test 4: Submit Answer
        results['submit_answer'] = test_submit_answer(
            session_id, 
            question['term_id'], 
            test_data
        )
        
        # Test 5: Verify Progress
        results['verify_progress'] = verify_progress_in_db(session_id)
    else:
        results['submit_answer'] = False
        results['verify_progress'] = False
    
    # Test 6: Pause Quiz
    results['pause_quiz'] = test_pause_quiz(session_id, test_data)
    
    # Test 7: Resume Quiz
    results['resume_quiz'] = test_resume_quiz(session_id, test_data)
    
    # Test 8: CloudWatch Logs
    results['cloudwatch_logs'] = check_cloudwatch_logs()
    
    # Print Summary
    print_header("Test Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    test_names = {
        'start_quiz': 'Start Quiz',
        'verify_session': 'Verify Session in Database',
        'get_question': 'Get Next Question',
        'submit_answer': 'Submit Answer',
        'verify_progress': 'Verify Progress in Database',
        'pause_quiz': 'Pause Quiz',
        'resume_quiz': 'Resume Quiz',
        'cloudwatch_logs': 'CloudWatch Logs'
    }
    
    for test_key, result in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if result else f"{Colors.RED}FAILED{Colors.RESET}"
        print(f"  {test_names[test_key]:35} {status}")
    
    print(f"\n{Colors.BOLD}Overall: {passed_tests}/{total_tests} tests passed{Colors.RESET}")
    
    if passed_tests == total_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Quiz Engine is fully functional.{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some tests failed. Review the output above.{Colors.RESET}\n")
        return False


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
