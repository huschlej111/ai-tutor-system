#!/usr/bin/env python3
"""
Test Quiz Engine via API Gateway (HTTP endpoints)
Tests authentication and basic quiz operations through API Gateway
"""
import boto3
import requests
import json
import sys
from datetime import datetime

# Get stack outputs
cf = boto3.client('cloudformation', region_name='us-east-1')
response = cf.describe_stacks(StackName='TutorSystemStack-dev')
outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}

API_URL = outputs['ApiUrl'].rstrip('/')
USER_POOL_ID = outputs['UserPoolId']
CLIENT_ID = outputs['UserPoolClientId']

print(f"API URL: {API_URL}")
print(f"User Pool ID: {USER_POOL_ID}")
print()

# Get test user credentials from environment or use defaults
TEST_EMAIL = "test123@test.com"
TEST_PASSWORD = "TestPass123!"

def register_test_user():
    """Register a test user via the proper /auth/register endpoint"""
    import uuid
    import time
    
    # Create unique test user
    unique_id = str(uuid.uuid4())[:8]
    email = f"apitest_{unique_id}@test.com"
    password = "TestPass123!"
    
    print(f"ℹ  Registering test user: {email}")
    
    response = requests.post(
        f"{API_URL}/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": "API",
            "last_name": "Test"
        },
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 201:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"ℹ  Response: {response.text}")
        return None, None
    
    print(f"✓ User registered successfully")
    
    # Wait a moment for user to be fully created
    time.sleep(2)
    
    return email, password

def authenticate():
    """Authenticate and get ID token"""
    # First register a new test user
    email, password = register_test_user()
    if not email:
        return None
    
    cognito = boto3.client('cognito-idp', region_name='us-east-1')
    
    try:
        response = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        return response['AuthenticationResult']['IdToken']
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None

def test_unauthenticated_request():
    """Test that protected endpoints reject unauthenticated requests"""
    print("=" * 70)
    print("Test 1: Unauthenticated Request (should return 401)")
    print("=" * 70)
    
    response = requests.post(
        f"{API_URL}/quiz/start",
        json={"domain_id": "test"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 401:
        print("✓ Correctly rejected with 401 Unauthorized")
        print(f"ℹ  Response: {response.json()}")
        return True
    else:
        print(f"❌ Expected 401, got {response.status_code}")
        print(f"ℹ  Response: {response.text}")
        return False

def test_authenticated_request(token):
    """Test that authenticated requests succeed"""
    print("\n" + "=" * 70)
    print("Test 2: Authenticated Request (should succeed)")
    print("=" * 70)
    
    # First create a domain with terms for testing
    print("ℹ  Creating test domain...")
    domain_response = requests.post(
        f"{API_URL}/domains",
        json={
            "name": "API Test Domain",
            "description": "Test domain for API Gateway testing"
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    
    if domain_response.status_code != 201:
        print(f"❌ Failed to create domain: {domain_response.status_code}")
        print(f"ℹ  Response: {domain_response.text}")
        return False
    
    domain = domain_response.json()
    # Handle nested response format
    if 'data' in domain and 'domain' in domain['data']:
        domain_data = domain['data']['domain']
    elif 'domain' in domain:
        domain_data = domain['domain']
    else:
        domain_data = domain
    
    domain_id = domain_data.get('id')
    if not domain_id:
        print(f"❌ No domain_id in response: {domain}")
        return False
    print(f"✓ Domain created: {domain_data.get('name', 'Unknown')} ({domain_id})")
    
    # Add some terms to the domain
    print("ℹ  Adding terms to domain...")
    terms_response = requests.post(
        f"{API_URL}/domains/{domain_id}/terms",
        json={
            "terms": [
                {"term": "Lambda", "definition": "AWS serverless compute service"},
                {"term": "API Gateway", "definition": "AWS managed API service"},
                {"term": "DynamoDB", "definition": "AWS NoSQL database service"}
            ]
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    
    if terms_response.status_code == 201:
        terms_result = terms_response.json()
        print(f"  ✓ Added {len(terms_result.get('terms', []))} terms")
    else:
        print(f"  ❌ Failed to add terms: {terms_response.status_code}")
        print(f"  ℹ  Response: {terms_response.text}")
        return False
    
    # Now test starting a quiz
    print("\nℹ  Starting quiz...")
    response = requests.post(
        f"{API_URL}/quiz/start",
        json={"domain_id": domain_id},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Quiz started successfully via API Gateway!")
        print(f"ℹ  Session ID: {result.get('session_id')}")
        print(f"ℹ  Total Questions: {result.get('total_questions')}")
        return True
    else:
        print(f"❌ Failed with status {response.status_code}")
        print(f"ℹ  Response: {response.text}")
        return False

def test_health_endpoint():
    """Test health endpoint (no auth required)"""
    print("\n" + "=" * 70)
    print("Test 3: Health Endpoint (no auth required)")
    print("=" * 70)
    
    response = requests.get(
        f"{API_URL}/quiz/evaluate/health",
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Health check passed!")
        print(f"ℹ  Status: {result.get('status')}")
        print(f"ℹ  Model Loaded: {result.get('model_loaded')}")
        return True
    else:
        print(f"❌ Health check failed with status {response.status_code}")
        print(f"ℹ  Response: {response.text}")
        return False

def main():
    """Run all API Gateway tests"""
    print("\n" + "=" * 70)
    print("Quiz Engine API Gateway Tests")
    print("=" * 70)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    results = []
    
    # Test 1: Unauthenticated request
    results.append(("Unauthenticated Request", test_unauthenticated_request()))
    
    # Test 2: Health endpoint
    results.append(("Health Endpoint", test_health_endpoint()))
    
    # Test 3: Authenticated request
    print("\nℹ  Authenticating...")
    token = authenticate()
    if token:
        print("✓ Authentication successful")
        results.append(("Authenticated Request", test_authenticated_request(token)))
    else:
        print("❌ Skipping authenticated tests (no token)")
        results.append(("Authenticated Request", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All API Gateway tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
