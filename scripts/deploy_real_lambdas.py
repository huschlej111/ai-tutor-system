#!/usr/bin/env python3
"""
Deploy real Lambda functions to LocalStack for UAT
Uses actual Lambda function code that connects to PostgreSQL
"""
import json
import boto3
import zipfile
import io
import os
from pathlib import Path
from botocore.exceptions import ClientError


def create_lambda_package_without_psycopg2(function_path):
    """Create a deployment package for a Lambda function without psycopg2 (using layer)"""
    
    # Create zip file
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the handler file
        handler_file = function_path / 'handler.py'
        if handler_file.exists():
            zip_file.write(handler_file, 'handler.py')
        
        # Add shared modules
        shared_dir = Path('src/shared')
        if shared_dir.exists():
            for shared_file in shared_dir.glob('*.py'):
                zip_file.write(shared_file, f'shared/{shared_file.name}')
        
        print(f"  📦 Package created for {function_path.name} (using psycopg2 layer)")
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def create_lambda_package(function_path):
    """Create a deployment package for a Lambda function with psycopg2-binary"""
    
    # Create zip file
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the handler file
        handler_file = function_path / 'handler.py'
        if handler_file.exists():
            zip_file.write(handler_file, 'handler.py')
        
        # Add shared modules
        shared_dir = Path('src/shared')
        if shared_dir.exists():
            for shared_file in shared_dir.glob('*.py'):
                zip_file.write(shared_file, f'shared/{shared_file.name}')
        
        # Add psycopg2 from the virtual environment
        import site
        
        # Find psycopg2 in site-packages
        psycopg2_path = None
        for site_dir in site.getsitepackages():
            potential_path = Path(site_dir) / 'psycopg2'
            if potential_path.exists():
                psycopg2_path = potential_path
                break
        
        if psycopg2_path:
            print(f"  📦 Including psycopg2-binary from {psycopg2_path}")
            # Add psycopg2 files to the package
            for psycopg2_file in psycopg2_path.rglob('*'):
                if psycopg2_file.is_file():
                    # Skip __pycache__ directories and .pyc files
                    if '__pycache__' not in str(psycopg2_file) and not psycopg2_file.name.endswith('.pyc'):
                        arc_name = f"psycopg2/{psycopg2_file.relative_to(psycopg2_path)}"
                        try:
                            zip_file.write(psycopg2_file, arc_name)
                        except Exception as e:
                            print(f"    ⚠️ Skipping {psycopg2_file}: {e}")
        else:
            print(f"  ⚠️ psycopg2 not found in site-packages")
        
        print(f"  📦 Package created for {function_path.name}")
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def deploy_lambda_function(lambda_client, function_name, function_path, description):
    """Deploy a real Lambda function to LocalStack"""
    
    print(f"📦 Packaging {function_name}...")
    
    # Create deployment package (without psycopg2, using layer instead)
    zip_content = create_lambda_package_without_psycopg2(function_path)
    
    # Environment variables for Lambda
    # Lambda functions run inside LocalStack container, connect to postgres container
    environment = {
        'Variables': {
            'DB_HOST': 'postgres',  # Container name in Docker network
            'DB_PORT': '5432',
            'DB_NAME': 'tutor_system',
            'DB_USER': 'tutor_user',
            'DB_PASSWORD': 'tutor_password',
            'ENVIRONMENT': 'local',
            'LOCALSTACK_ENDPOINT': 'http://localhost:4566',
            'AWS_ENDPOINT_URL': 'http://localhost:4566'
        }
    }
    
    # Use the psycopg2 layer
    layers = ['arn:aws:lambda:us-east-1:000000000000:layer:psycopg2-layer:1']
    
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role='arn:aws:iam::000000000000:role/lambda-role',
            Handler='handler.lambda_handler',
            Code={'ZipFile': zip_content},
            Description=description,
            Timeout=30,
            MemorySize=256,
            Environment=environment,
            Layers=layers
        )
        print(f"✅ Deployed Lambda function: {function_name}")
        return response['FunctionArn']
        
    except ClientError as e:
        if 'ResourceConflictException' in str(e):
            # Update existing function
            try:
                lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_content
                )
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Environment=environment,
                    Layers=layers
                )
                print(f"✅ Updated Lambda function: {function_name}")
                
                # Get function ARN
                response = lambda_client.get_function(FunctionName=function_name)
                return response['Configuration']['FunctionArn']
                
            except Exception as update_error:
                print(f"❌ Failed to update {function_name}: {update_error}")
                return None
        else:
            print(f"❌ Failed to deploy {function_name}: {e}")
            return None


def setup_api_gateway(apigateway_client, lambda_arns):
    """Setup API Gateway with real Lambda integrations"""
    
    print("🌐 Setting up API Gateway...")
    
    try:
        # Create REST API
        api_response = apigateway_client.create_rest_api(
            name='TutorSystemAPI',
            description='Real API for Know-It-All Tutor System',
            endpointConfiguration={'types': ['REGIONAL']}
        )
        
        api_id = api_response['id']
        print(f"✅ Created API Gateway: {api_id}")
        
        # Get root resource
        resources = apigateway_client.get_resources(restApiId=api_id)
        root_resource_id = resources['items'][0]['id']
        
        # Create resource structure
        resources_to_create = [
            ('progress', root_resource_id),
            ('domains', root_resource_id),
            ('quiz', root_resource_id)
        ]
        
        created_resources = {}
        
        for resource_name, parent_id in resources_to_create:
            resource = apigateway_client.create_resource(
                restApiId=api_id,
                parentId=parent_id,
                pathPart=resource_name
            )
            created_resources[resource_name] = resource['id']
            print(f"✅ Created resource: /{resource_name}")
        
        # Create dashboard endpoint under progress
        dashboard_resource = apigateway_client.create_resource(
            restApiId=api_id,
            parentId=created_resources['progress'],
            pathPart='dashboard'
        )
        
        # Setup methods and integrations
        endpoints = [
            {
                'resource_id': dashboard_resource['id'],
                'method': 'GET',
                'lambda_arn': lambda_arns.get('progress_tracking'),
                'path': '/progress/dashboard'
            },
            {
                'resource_id': created_resources['domains'],
                'method': 'GET',
                'lambda_arn': lambda_arns.get('domain_management'),
                'path': '/domains'
            },
            {
                'resource_id': created_resources['domains'],
                'method': 'POST',
                'lambda_arn': lambda_arns.get('domain_management'),
                'path': '/domains'
            }
        ]
        
        for endpoint in endpoints:
            if endpoint['lambda_arn']:
                # Create method
                apigateway_client.put_method(
                    restApiId=api_id,
                    resourceId=endpoint['resource_id'],
                    httpMethod=endpoint['method'],
                    authorizationType='NONE'
                )
                
                # Create integration
                lambda_uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{endpoint['lambda_arn']}/invocations"
                
                apigateway_client.put_integration(
                    restApiId=api_id,
                    resourceId=endpoint['resource_id'],
                    httpMethod=endpoint['method'],
                    type='AWS_PROXY',
                    integrationHttpMethod='POST',
                    uri=lambda_uri
                )
                
                print(f"✅ Created {endpoint['method']} {endpoint['path']}")
        
        # Deploy API
        apigateway_client.create_deployment(
            restApiId=api_id,
            stageName='dev'
        )
        
        api_url = f"http://localhost:4566/restapis/{api_id}/dev/_user_request_"
        print(f"✅ API deployed at: {api_url}")
        
        return api_url
        
    except ClientError as e:
        if 'ConflictException' in str(e):
            print("✅ API Gateway already exists")
            # Try to find existing API
            apis = apigateway_client.get_rest_apis()
            for api in apis['items']:
                if api['name'] == 'TutorSystemAPI':
                    api_id = api['id']
                    api_url = f"http://localhost:4566/restapis/{api_id}/dev/_user_request_"
                    return api_url
        else:
            print(f"❌ Failed to setup API Gateway: {e}")
            return None


def main():
    """Deploy real Lambda functions for UAT"""
    
    print("🚀 Deploying REAL Lambda functions for UAT...")
    print("This will create actual Lambda functions that connect to PostgreSQL")
    
    # Configure LocalStack clients
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
    
    # Lambda functions to deploy
    lambda_functions = {
        'domain_management': {
            'path': Path('src/lambda_functions/domain_management'),
            'description': 'Domain management API - create, read, update, delete domains'
        },
        'progress_tracking': {
            'path': Path('src/lambda_functions/progress_tracking'),
            'description': 'Progress tracking API - dashboard data and user progress'
        },
        'quiz_engine': {
            'path': Path('src/lambda_functions/quiz_engine'),
            'description': 'Quiz engine API - start quiz, submit answers, get results'
        },
        'answer_evaluation': {
            'path': Path('src/lambda_functions/answer_evaluation'),
            'description': 'Answer evaluation API - ML-powered answer scoring'
        }
    }
    
    # Deploy Lambda functions
    lambda_arns = {}
    
    for function_name, config in lambda_functions.items():
        if config['path'].exists():
            arn = deploy_lambda_function(
                lambda_client,
                function_name,
                config['path'],
                config['description']
            )
            if arn:
                lambda_arns[function_name] = arn
        else:
            print(f"⚠️ Lambda function path not found: {config['path']}")
    
    if not lambda_arns:
        print("❌ No Lambda functions were deployed successfully")
        return 1
    
    # Setup API Gateway
    api_url = setup_api_gateway(apigateway_client, lambda_arns)
    
    if api_url:
        # Update frontend environment
        update_frontend_env(api_url)
        
        print(f"\n✅ Real Lambda deployment completed!")
        print(f"🌐 API Base URL: {api_url}")
        print(f"\n📋 Deployed functions:")
        for name, arn in lambda_arns.items():
            print(f"  - {name}: {arn}")
        
        print(f"\n🎯 Next steps:")
        print("1. Restart the frontend: cd frontend && npm run dev")
        print("2. The dashboard will now use REAL Lambda functions")
        print("3. Data will be stored in PostgreSQL database")
        print("4. Full AWS-compatible functionality for UAT")
        
        return 0
    else:
        print("❌ Failed to setup API Gateway")
        return 1


def update_frontend_env(api_url):
    """Update frontend environment with real API URL"""
    env_file = 'frontend/.env.local'
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('VITE_API_BASE_URL='):
                updated_lines.append(f'VITE_API_BASE_URL={api_url}')
            else:
                updated_lines.append(line)
        
        with open(env_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print(f"✅ Updated {env_file} with real API URL")
        
    except Exception as e:
        print(f"⚠️ Could not update frontend environment: {e}")


if __name__ == "__main__":
    import sys
    sys.exit(main())