#!/usr/bin/env python3
"""
Setup mock API endpoints in LocalStack for UAT
Creates basic API Gateway and Lambda functions to support frontend testing
"""
import json
import boto3
import zipfile
import io
from botocore.exceptions import ClientError


def create_mock_lambda_function(lambda_client, function_name, handler_code):
    """Create a mock Lambda function"""
    
    # Create zip file with the handler code
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', handler_code)
    zip_buffer.seek(0)
    
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role='arn:aws:iam::000000000000:role/lambda-role',
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_buffer.getvalue()},
            Description=f'Mock function for {function_name}',
            Timeout=30,
            MemorySize=128
        )
        print(f"✅ Created Lambda function: {function_name}")
        return response['FunctionArn']
    except ClientError as e:
        if 'ResourceConflictException' in str(e):
            print(f"✅ Lambda function already exists: {function_name}")
            # Get existing function ARN
            response = lambda_client.get_function(FunctionName=function_name)
            return response['Configuration']['FunctionArn']
        else:
            print(f"❌ Failed to create Lambda function {function_name}: {e}")
            return None


def setup_mock_api():
    """Setup mock API Gateway and Lambda functions for UAT"""
    
    print("🚀 Setting up mock API for UAT...")
    
    # Configure for LocalStack
    lambda_client = boto3.client(
        'lambda',
        endpoint_url='http://localhost:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1'
    )
    
    apigateway_client = boto3.client(
        'apigateway',
        endpoint_url='http://localhost:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='us-east-1'
    )
    
    # Mock dashboard Lambda function
    dashboard_code = '''
import json

def lambda_handler(event, context):
    # Mock dashboard data for UAT
    mock_data = {
        "user_id": "test-user-123",
        "total_domains": 2,
        "domains": [
            {
                "id": "domain-1",
                "name": "AWS Fundamentals",
                "description": "Basic AWS concepts and services",
                "term_count": 15,
                "completion_percentage": 67,
                "mastery_percentage": 45,
                "mastery_breakdown": {
                    "mastered": 7,
                    "proficient": 3,
                    "developing": 2,
                    "needs_practice": 2,
                    "not_attempted": 1
                },
                "last_activity": "2026-01-06T12:00:00Z"
            },
            {
                "id": "domain-2", 
                "name": "Python Programming",
                "description": "Python language fundamentals",
                "term_count": 20,
                "completion_percentage": 30,
                "mastery_percentage": 15,
                "mastery_breakdown": {
                    "mastered": 3,
                    "proficient": 2,
                    "developing": 1,
                    "needs_practice": 4,
                    "not_attempted": 10
                },
                "last_activity": "2026-01-05T15:30:00Z"
            }
        ],
        "overall_stats": {
            "total_terms": 35,
            "mastered_terms": 10,
            "proficient_terms": 5,
            "developing_terms": 3,
            "needs_practice_terms": 6,
            "not_attempted_terms": 11,
            "overall_completion_percentage": 49,
            "overall_mastery_percentage": 29
        },
        "recent_activity": [
            {
                "timestamp": "2026-01-06T12:00:00Z",
                "is_correct": True,
                "similarity_score": 0.92,
                "term": "EC2",
                "domain_name": "AWS Fundamentals"
            },
            {
                "timestamp": "2026-01-06T11:45:00Z",
                "is_correct": False,
                "similarity_score": 0.65,
                "term": "Lambda",
                "domain_name": "AWS Fundamentals"
            },
            {
                "timestamp": "2026-01-05T15:30:00Z",
                "is_correct": True,
                "similarity_score": 0.88,
                "term": "List Comprehension",
                "domain_name": "Python Programming"
            }
        ],
        "learning_streaks": {
            "current_streak": 3,
            "longest_streak": 7
        }
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(mock_data)
    }
'''
    
    # Mock domains Lambda function
    domains_code = '''
import json

def lambda_handler(event, context):
    # Mock domains data
    mock_domains = [
        {
            "id": "domain-1",
            "name": "AWS Fundamentals", 
            "description": "Basic AWS concepts and services",
            "term_count": 15,
            "user_id": "test-user-123",
            "created_at": "2026-01-01T10:00:00Z",
            "updated_at": "2026-01-06T12:00:00Z"
        },
        {
            "id": "domain-2",
            "name": "Python Programming",
            "description": "Python language fundamentals", 
            "term_count": 20,
            "user_id": "test-user-123",
            "created_at": "2026-01-02T14:00:00Z",
            "updated_at": "2026-01-05T15:30:00Z"
        }
    ]
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(mock_domains)
    }
'''
    
    # Create Lambda functions
    dashboard_arn = create_mock_lambda_function(lambda_client, 'mock-dashboard', dashboard_code)
    domains_arn = create_mock_lambda_function(lambda_client, 'mock-domains', domains_code)
    
    if not dashboard_arn or not domains_arn:
        print("❌ Failed to create Lambda functions")
        return False
    
    # Create API Gateway
    try:
        # Create REST API
        api_response = apigateway_client.create_rest_api(
            name='TutorSystemMockAPI',
            description='Mock API for UAT testing',
            endpointConfiguration={
                'types': ['REGIONAL']
            }
        )
        
        api_id = api_response['id']
        print(f"✅ Created API Gateway: {api_id}")
        
        # Get root resource
        resources = apigateway_client.get_resources(restApiId=api_id)
        root_resource_id = None
        for resource in resources['items']:
            if resource['path'] == '/':
                root_resource_id = resource['id']
                break
        
        # Create /progress resource
        progress_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_resource_id,
            pathPart='progress'
        )
        
        # Create /progress/dashboard resource
        dashboard_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=progress_resource['id'],
            pathPart='dashboard'
        )
        
        # Create /domains resource
        domains_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=root_resource_id,
            pathPart='domains'
        )
        
        # Create GET method for dashboard
        apigateway_client.put_method(
            restApiId=api_id,
            resourceId=dashboard_resource['id'],
            httpMethod='GET',
            authorizationType='NONE'
        )
        
        # Create GET method for domains
        apigateway_client.put_method(
            restApiId=api_id,
            resourceId=domains_resource['id'],
            httpMethod='GET',
            authorizationType='NONE'
        )
        
        # Set up Lambda integrations
        lambda_uri_dashboard = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{dashboard_arn}/invocations"
        lambda_uri_domains = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{domains_arn}/invocations"
        
        # Dashboard integration
        apigateway_client.put_integration(
            restApiId=api_id,
            resourceId=dashboard_resource['id'],
            httpMethod='GET',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri_dashboard
        )
        
        # Domains integration
        apigateway_client.put_integration(
            restApiId=api_id,
            resourceId=domains_resource['id'],
            httpMethod='GET',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri_domains
        )
        
        # Deploy API
        deployment = apigateway_client.create_deployment(
            restApiId=api_id,
            stageName='dev'
        )
        
        api_url = f"http://localhost:4566/restapis/{api_id}/dev/_user_request_"
        
        print(f"✅ API Gateway deployed successfully!")
        print(f"🌐 API Base URL: {api_url}")
        print(f"📊 Dashboard endpoint: {api_url}/progress/dashboard")
        print(f"📁 Domains endpoint: {api_url}/domains")
        
        # Update frontend environment
        update_frontend_env(api_url)
        
        return True
        
    except ClientError as e:
        if 'ConflictException' in str(e):
            print("✅ API Gateway already exists")
            return True
        else:
            print(f"❌ Failed to create API Gateway: {e}")
            return False


def update_frontend_env(api_url):
    """Update frontend environment with API URL"""
    env_file = 'frontend/.env.local'
    
    try:
        # Read existing content
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update API base URL
        lines = content.split('\n')
        updated_lines = []
        api_url_updated = False
        
        for line in lines:
            if line.startswith('VITE_API_BASE_URL='):
                updated_lines.append(f'VITE_API_BASE_URL={api_url}')
                api_url_updated = True
            else:
                updated_lines.append(line)
        
        # Add API URL if not found
        if not api_url_updated:
            updated_lines.append(f'VITE_API_BASE_URL={api_url}')
        
        # Write back
        with open(env_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print(f"✅ Updated {env_file} with API URL")
        print("🔄 Please restart the frontend server to pick up the new API URL")
        
    except Exception as e:
        print(f"⚠️ Could not update frontend environment: {e}")
        print(f"📝 Please manually update VITE_API_BASE_URL={api_url} in {env_file}")


def main():
    """Main entry point"""
    try:
        success = setup_mock_api()
        if success:
            print("\n✅ Mock API setup completed successfully!")
            print("\n🎯 Next steps:")
            print("1. Restart the frontend server: cd frontend && npm run dev")
            print("2. The dashboard should now load with mock data")
            print("3. You can test domain management and other features")
            return 0
        else:
            print("\n❌ Mock API setup failed!")
            return 1
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())