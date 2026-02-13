#!/usr/bin/env python3
"""
Test script for deployed Answer Evaluator Lambda function
Tests the container-based Lambda deployment directly via AWS Lambda API

This script validates:
- Lambda function is deployed and accessible
- Model loads successfully
- Similarity scoring works correctly
- Feedback generation is appropriate
- CloudWatch logs are being created
"""
import boto3
import json
import sys
import time
from typing import Dict, Any, List

# AWS Configuration
REGION = 'us-east-1'
FUNCTION_NAME = 'answer-evaluator'

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=REGION)
logs_client = boto3.client('logs', region_name=REGION)


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.RESET}")


def invoke_lambda(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke the Answer Evaluator Lambda function
    
    Args:
        payload: Event payload to send to Lambda
        
    Returns:
        Lambda response
    """
    try:
        response = lambda_client.invoke(
            FunctionName=FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        return response_payload
        
    except Exception as e:
        print_error(f"Lambda invocation failed: {e}")
        return None


def test_lambda_deployment():
    """Test 1: Verify Lambda function is deployed"""
    print_header("Test 1: Lambda Deployment Verification")
    
    try:
        response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
        
        config = response['Configuration']
        print_success(f"Lambda function found: {config['FunctionName']}")
        print_info(f"  Runtime: {config['Runtime']}")
        print_info(f"  Memory: {config['MemorySize']} MB")
        print_info(f"  Timeout: {config['Timeout']} seconds")
        print_info(f"  Package Type: {config.get('PackageType', 'Zip')}")
        print_info(f"  Last Modified: {config['LastModified']}")
        
        return True
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print_error(f"Lambda function '{FUNCTION_NAME}' not found")
        return False
    except Exception as e:
        print_error(f"Failed to get Lambda function: {e}")
        return False


def test_basic_evaluation():
    """Test 2: Basic answer evaluation"""
    print_header("Test 2: Basic Answer Evaluation")
    
    test_cases = [
        {
            "name": "Identical answers",
            "answer": "AWS Lambda is a serverless compute service",
            "correct_answer": "AWS Lambda is a serverless compute service",
            "expected_min_similarity": 0.95
        },
        {
            "name": "Semantically similar answers",
            "answer": "Lambda is a serverless computing service",
            "correct_answer": "AWS Lambda is a serverless compute service",
            "expected_min_similarity": 0.70
        },
        {
            "name": "Partially correct answer",
            "answer": "Lambda is a cloud service",
            "correct_answer": "AWS Lambda is a serverless compute service",
            "expected_min_similarity": 0.40
        },
        {
            "name": "Incorrect answer",
            "answer": "Lambda is a database service",
            "correct_answer": "AWS Lambda is a serverless compute service",
            "expected_min_similarity": 0.0
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n{Colors.BOLD}Testing: {test_case['name']}{Colors.RESET}")
        
        payload = {
            "answer": test_case["answer"],
            "correct_answer": test_case["correct_answer"]
        }
        
        response = invoke_lambda(payload)
        
        if response is None:
            print_error("Lambda invocation failed")
            all_passed = False
            continue
        
        # Check status code
        if response.get('statusCode') != 200:
            print_error(f"Expected status 200, got {response.get('statusCode')}")
            print_info(f"Response: {json.dumps(response, indent=2)}")
            all_passed = False
            continue
        
        # Parse body
        try:
            body = json.loads(response['body'])
        except:
            body = response.get('body', {})
        
        similarity = body.get('similarity')
        feedback = body.get('feedback')
        
        if similarity is None:
            print_error("No similarity score in response")
            all_passed = False
            continue
        
        print_info(f"  Answer: {test_case['answer'][:50]}...")
        print_info(f"  Similarity: {similarity:.4f}")
        print_info(f"  Feedback: {feedback}")
        
        # Validate similarity score
        if not (0.0 <= similarity <= 1.0):
            print_error(f"Similarity score {similarity} out of range [0.0, 1.0]")
            all_passed = False
        elif similarity >= test_case['expected_min_similarity']:
            print_success(f"Similarity score {similarity:.4f} meets expectation (>= {test_case['expected_min_similarity']})")
        else:
            print_error(f"Similarity score {similarity:.4f} below expectation (>= {test_case['expected_min_similarity']})")
            all_passed = False
    
    return all_passed


def test_feedback_generation():
    """Test 3: Feedback generation for different similarity ranges"""
    print_header("Test 3: Feedback Generation")
    
    # Test with answers that should produce different feedback levels
    test_cases = [
        {
            "name": "Excellent match (>= 0.85)",
            "answer": "Serverless compute service that runs code",
            "correct_answer": "Serverless compute service that runs code",
            "expected_keyword": "Excellent"
        },
        {
            "name": "Good match (0.70-0.85)",
            "answer": "Serverless computing platform",
            "correct_answer": "Serverless compute service",
            "expected_keyword": "Good"
        },
        {
            "name": "Partial match (0.50-0.70)",
            "answer": "Cloud computing service",
            "correct_answer": "Serverless compute service",
            "expected_keyword": "Partially"
        },
        {
            "name": "Incorrect (< 0.50)",
            "answer": "Database storage system",
            "correct_answer": "Serverless compute service",
            "expected_keyword": "Incorrect"
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n{Colors.BOLD}Testing: {test_case['name']}{Colors.RESET}")
        
        payload = {
            "answer": test_case["answer"],
            "correct_answer": test_case["correct_answer"]
        }
        
        response = invoke_lambda(payload)
        
        if response is None or response.get('statusCode') != 200:
            print_error("Lambda invocation failed")
            all_passed = False
            continue
        
        try:
            body = json.loads(response['body'])
        except:
            body = response.get('body', {})
        
        similarity = body.get('similarity')
        feedback = body.get('feedback')
        
        print_info(f"  Similarity: {similarity:.4f}")
        print_info(f"  Feedback: {feedback}")
        
        # Check if expected keyword is in feedback
        if test_case['expected_keyword'].lower() in feedback.lower():
            print_success(f"Feedback contains expected keyword: '{test_case['expected_keyword']}'")
        else:
            print_error(f"Feedback missing expected keyword: '{test_case['expected_keyword']}'")
            all_passed = False
    
    return all_passed


def test_error_handling():
    """Test 4: Error handling for invalid inputs"""
    print_header("Test 4: Error Handling")
    
    test_cases = [
        {
            "name": "Missing answer field",
            "payload": {"correct_answer": "test"},
            "expected_status": 400
        },
        {
            "name": "Missing correct_answer field",
            "payload": {"answer": "test"},
            "expected_status": 400
        },
        {
            "name": "Empty answer",
            "payload": {"answer": "", "correct_answer": "test"},
            "expected_status": 400
        },
        {
            "name": "Empty correct_answer",
            "payload": {"answer": "test", "correct_answer": ""},
            "expected_status": 400
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n{Colors.BOLD}Testing: {test_case['name']}{Colors.RESET}")
        
        response = invoke_lambda(test_case['payload'])
        
        if response is None:
            print_error("Lambda invocation failed")
            all_passed = False
            continue
        
        status_code = response.get('statusCode')
        
        if status_code == test_case['expected_status']:
            print_success(f"Correct error status: {status_code}")
        else:
            print_error(f"Expected status {test_case['expected_status']}, got {status_code}")
            all_passed = False
        
        # Show error message
        try:
            body = json.loads(response['body'])
            error_msg = body.get('error', 'No error message')
            print_info(f"  Error message: {error_msg}")
        except:
            pass
    
    return all_passed


def test_cloudwatch_logs():
    """Test 5: Verify CloudWatch logs are being created"""
    print_header("Test 5: CloudWatch Logs Verification")
    
    log_group_name = f'/aws/lambda/{FUNCTION_NAME}'
    
    try:
        # Check if log group exists
        response = logs_client.describe_log_groups(
            logGroupNamePrefix=log_group_name
        )
        
        if not response['logGroups']:
            print_error(f"Log group '{log_group_name}' not found")
            return False
        
        print_success(f"Log group found: {log_group_name}")
        
        # Get recent log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not streams_response['logStreams']:
            print_error("No log streams found")
            return False
        
        print_success(f"Found {len(streams_response['logStreams'])} recent log streams")
        
        # Get recent log events from the most recent stream
        latest_stream = streams_response['logStreams'][0]
        print_info(f"  Latest stream: {latest_stream['logStreamName']}")
        print_info(f"  Last event: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_stream['lastEventTime']/1000))}")
        
        # Try to get some log events
        events_response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=latest_stream['logStreamName'],
            limit=10,
            startFromHead=False
        )
        
        if events_response['events']:
            print_success(f"Retrieved {len(events_response['events'])} log events")
            print_info("  Recent log messages:")
            for event in events_response['events'][-3:]:
                message = event['message'].strip()
                if len(message) > 100:
                    message = message[:100] + "..."
                print_info(f"    {message}")
        
        return True
        
    except logs_client.exceptions.ResourceNotFoundException:
        print_error(f"Log group '{log_group_name}' not found")
        return False
    except Exception as e:
        print_error(f"Failed to check CloudWatch logs: {e}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   Answer Evaluator Lambda - Deployment Test Suite         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    print_info(f"Testing Lambda function: {FUNCTION_NAME}")
    print_info(f"Region: {REGION}")
    
    results = {}
    
    # Run tests
    results['deployment'] = test_lambda_deployment()
    
    if results['deployment']:
        results['basic_evaluation'] = test_basic_evaluation()
        results['feedback_generation'] = test_feedback_generation()
        results['error_handling'] = test_error_handling()
        results['cloudwatch_logs'] = test_cloudwatch_logs()
    else:
        print_error("\nSkipping remaining tests due to deployment verification failure")
        return False
    
    # Print summary
    print_header("Test Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if result else f"{Colors.RED}FAILED{Colors.RESET}"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n{Colors.BOLD}Overall: {passed_tests}/{total_tests} tests passed{Colors.RESET}")
    
    if passed_tests == total_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Answer Evaluator Lambda is working correctly.{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed. Please review the output above.{Colors.RESET}\n")
        return False


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
