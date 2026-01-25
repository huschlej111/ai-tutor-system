#!/usr/bin/env python3
"""
LocalStack setup script for Know-It-All Tutor System
Sets up local AWS services for development and testing
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import requests
from botocore.config import Config


class LocalStackSetup:
    """Setup and manage LocalStack for local development"""
    
    def __init__(self, endpoint_url: str = "http://localhost:4566"):
        self.endpoint_url = endpoint_url
        self.region = "us-east-1"
        
        # Configure boto3 clients for LocalStack
        self.config = Config(
            region_name=self.region,
            retries={'max_attempts': 3, 'mode': 'standard'}
        )
        
        self.session = boto3.Session()
        self._clients = {}
        self._account_id = None  # Cache for account ID
    
    def get_account_id(self) -> str:
        """
        Get AWS Account ID using STS service with caching
        
        Returns:
            str: AWS Account ID
        """
        if self._account_id is None:
            try:
                sts_client = self.get_client('sts')
                response = sts_client.get_caller_identity()
                self._account_id = response['Account']
                print(f"✓ Retrieved AWS Account ID: {self._account_id}")
            except Exception as e:
                print(f"⚠ Failed to retrieve account ID via STS: {e}")
                # Fallback to LocalStack default for compatibility
                self._account_id = "000000000000"
                print(f"✓ Using fallback Account ID: {self._account_id}")
        
        return self._account_id
    
    def get_client(self, service_name: str):
        """Get or create a boto3 client for LocalStack"""
        if service_name not in self._clients:
            self._clients[service_name] = self.session.client(
                service_name,
                endpoint_url=self.endpoint_url,
                aws_access_key_id="test",
                aws_secret_access_key="test",
                region_name=self.region,
                config=self.config
            )
        return self._clients[service_name]
    
    def wait_for_localstack(self, timeout: int = 60) -> bool:
        """Wait for LocalStack to be ready"""
        print("Waiting for LocalStack to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try the health endpoint first
                response = requests.get(f"{self.endpoint_url}/health", timeout=5)
                if response.status_code == 200:
                    # Even if empty, a 200 response means LocalStack is ready
                    print(f"\nLocalStack is ready! Health endpoint responded with 200")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            # Alternative: try to list S3 buckets as a connectivity test
            try:
                s3 = self.get_client('s3')
                s3.list_buckets()
                print(f"\nLocalStack is ready! S3 service is responding")
                return True
            except Exception:
                pass
            
            print(".", end="", flush=True)
            time.sleep(2)
        
        print(f"\nTimeout waiting for LocalStack after {timeout} seconds")
        return False
    
    def create_s3_buckets(self) -> None:
        """Create S3 buckets for the application"""
        s3 = self.get_client('s3')
        
        buckets = [
            "tutor-system-uploads-local",
            "tutor-system-static-local",
            "tutor-system-ml-models-local",
            "tutor-system-backups-local"
        ]
        
        for bucket_name in buckets:
            try:
                s3.create_bucket(Bucket=bucket_name)
                print(f"✓ Created S3 bucket: {bucket_name}")
                
                # Enable versioning for backup bucket
                if "backups" in bucket_name:
                    s3.put_bucket_versioning(
                        Bucket=bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    print(f"  ✓ Enabled versioning for {bucket_name}")
                    
            except Exception as e:
                if "BucketAlreadyExists" in str(e):
                    print(f"✓ S3 bucket already exists: {bucket_name}")
                else:
                    print(f"✗ Failed to create S3 bucket {bucket_name}: {e}")
    
    def create_kms_keys(self) -> None:
        """Create KMS keys for encryption"""
        kms = self.get_client('kms')
        account_id = self.get_account_id()
        
        keys = [
            {
                'Description': 'Tutor System Secrets Manager encryption key',
                'KeyUsage': 'ENCRYPT_DECRYPT',
                'KeySpec': 'SYMMETRIC_DEFAULT',
                'Policy': json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "Enable IAM User Permissions",
                            "Effect": "Allow",
                            "Principal": {"AWS": f"arn:aws:iam::{account_id}:root"},
                            "Action": "kms:*",
                            "Resource": "*"
                        },
                        {
                            "Sid": "Allow Secrets Manager",
                            "Effect": "Allow",
                            "Principal": {"Service": "secretsmanager.amazonaws.com"},
                            "Action": [
                                "kms:Decrypt",
                                "kms:GenerateDataKey",
                                "kms:CreateGrant"
                            ],
                            "Resource": "*"
                        }
                    ]
                })
            }
        ]
        
        for key_config in keys:
            try:
                response = kms.create_key(**key_config)
                key_id = response['KeyMetadata']['KeyId']
                
                # Create alias for easier reference
                kms.create_alias(
                    AliasName='alias/tutor-system-secrets',
                    TargetKeyId=key_id
                )
                
                print(f"✓ Created KMS key: {key_id}")
                print(f"  ✓ Created alias: alias/tutor-system-secrets")
                
            except Exception as e:
                if "AlreadyExistsException" in str(e):
                    print(f"✓ KMS key already exists")
                else:
                    print(f"✗ Failed to create KMS key: {e}")
    
    def create_secrets(self) -> None:
        """Create secrets in AWS Secrets Manager with rotation configuration"""
        secrets_manager = self.get_client('secretsmanager')
        account_id = self.get_account_id()

        db_host = 'postgres' if os.path.exists('/.dockerenv') else 'localhost'
        
        secrets = [
            {
                'Name': 'tutor-system/database',
                'SecretString': json.dumps({
                    'host': db_host,
                    'port': 5432,
                    'database': 'tutor_system',
                    'username': 'tutor_user',
                    'password': 'tutor_password'
                }),
                'Description': 'Database connection credentials for local development',
                'KmsKeyId': 'alias/tutor-system-secrets'
            },
            {
                'Name': 'tutor-system/jwt-secret',
                'SecretString': json.dumps({
                    'secret': 'local-development-secret-key-change-in-production',
                    'algorithm': 'HS256',
                    'expiration_hours': 24
                }),
                'Description': 'JWT configuration for local development',
                'KmsKeyId': 'alias/tutor-system-secrets'
            },
            {
                'Name': 'tutor-system/ml-model',
                'SecretString': json.dumps({
                    'model_path': './final_similarity_model',
                    'similarity_threshold': 0.7,
                    'batch_size': 32
                }),
                'Description': 'ML model configuration',
                'KmsKeyId': 'alias/tutor-system-secrets'
            }
        ]
        
        for secret in secrets:
            try:
                response = secrets_manager.create_secret(**secret)
                print(f"✓ Created secret: {secret['Name']}")
                
                # Configure automatic rotation for local development (2 days)
                if secret['Name'] in ['tutor-system/database', 'tutor-system/jwt']:
                    try:
                        secrets_manager.rotate_secret(
                            SecretId=secret['Name'],
                            RotationLambdaArn=f"arn:aws:lambda:{self.region}:{account_id}:function:tutor-secrets-rotation",
                            RotationRules={
                                'AutomaticallyAfterDays': 2  # 2 days for local development
                            }
                        )
                        print(f"  ✓ Configured 2-day rotation for {secret['Name']}")
                    except Exception as rotation_error:
                        print(f"  ⚠ Could not configure rotation for {secret['Name']}: {rotation_error}")
                        print(f"    (Rotation Lambda may not exist yet)")
                
            except Exception as e:
                if "ResourceExistsException" in str(e):
                    print(f"✓ Secret already exists: {secret['Name']}")
                    
                    # Try to update rotation configuration for existing secrets
                    if secret['Name'] in ['tutor-system/database', 'tutor-system/jwt']:
                        try:
                            secrets_manager.rotate_secret(
                                SecretId=secret['Name'],
                                RotationLambdaArn=f"arn:aws:lambda:{self.region}:{account_id}:function:tutor-secrets-rotation",
                                RotationRules={
                                    'AutomaticallyAfterDays': 2
                                }
                            )
                            print(f"  ✓ Updated rotation to 2 days for existing secret: {secret['Name']}")
                        except Exception as rotation_error:
                            print(f"  ⚠ Could not update rotation for {secret['Name']}: {rotation_error}")
                else:
                    print(f"✗ Failed to create secret {secret['Name']}: {e}")
    
    def create_cognito_resources(self) -> None:
        """Create Cognito User Pool and App Client"""
        cognito = self.get_client('cognito-idp')
        account_id = self.get_account_id()
        
        try:
            # Create User Pool
            user_pool_response = cognito.create_user_pool(
                PoolName='TutorSystemUserPool',
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8,
                        'RequireUppercase': True,
                        'RequireLowercase': True,
                        'RequireNumbers': True,
                        'RequireSymbols': False
                    }
                },
                AutoVerifiedAttributes=['email'],
                AliasAttributes=['email'],
                UsernameAttributes=['email'],
                EmailConfiguration={
                    'EmailSendingAccount': 'DEVELOPER',
                    'SourceArn': f'arn:aws:ses:us-east-1:{account_id}:identity/noreply@know-it-all-tutor.com',
                    'ReplyToEmailAddress': 'noreply@know-it-all-tutor.com'
                },
                VerificationMessageTemplate={
                    'DefaultEmailOption': 'CONFIRM_WITH_CODE',
                    'EmailSubject': 'Know-It-All Tutor - Verify your email',
                    'EmailMessage': 'Welcome to Know-It-All Tutor! Your verification code is {####}'
                },
                UserPoolTags={
                    'Environment': 'local',
                    'Application': 'know-it-all-tutor'
                }
            )
            
            user_pool_id = user_pool_response['UserPool']['Id']
            print(f"✓ Created Cognito User Pool: {user_pool_id}")
            
            # Create App Client
            app_client_response = cognito.create_user_pool_client(
                UserPoolId=user_pool_id,
                ClientName='TutorSystemWebClient',
                GenerateSecret=False,  # Public client for web app
                RefreshTokenValidity=30,
                AccessTokenValidity=60,
                IdTokenValidity=60,
                TokenValidityUnits={
                    'AccessToken': 'minutes',
                    'IdToken': 'minutes',
                    'RefreshToken': 'days'
                },
                ReadAttributes=[
                    'email',
                    'email_verified',
                    'given_name',
                    'family_name',
                    'preferred_username'
                ],
                WriteAttributes=[
                    'email',
                    'given_name',
                    'family_name',
                    'preferred_username'
                ],
                ExplicitAuthFlows=[
                    'ALLOW_USER_SRP_AUTH',
                    'ALLOW_USER_PASSWORD_AUTH',
                    'ALLOW_REFRESH_TOKEN_AUTH'
                ],
                PreventUserExistenceErrors='ENABLED',
                EnableTokenRevocation=True
            )
            
            client_id = app_client_response['UserPoolClient']['ClientId']
            print(f"✓ Created Cognito App Client: {client_id}")
            
            # Create test users
            self._create_test_users(cognito, user_pool_id)
            
            # Update frontend environment
            self._update_frontend_env(user_pool_id, client_id)
            
        except Exception as e:
            if "ResourceConflictException" in str(e):
                print(f"✓ Cognito User Pool already exists")
            else:
                print(f"✗ Failed to create Cognito resources: {e}")
    
    def _create_test_users(self, cognito, user_pool_id):
        """Create test users for development"""
        test_users = [
            {
                'username': 'admin@example.com',
                'email': 'admin@example.com',
                'given_name': 'Admin',
                'family_name': 'User',
                'temporary_password': 'TempPass123!',
                'permanent_password': 'admin123'
            },
            {
                'username': 'test@example.com',
                'email': 'test@example.com',
                'given_name': 'Test',
                'family_name': 'User',
                'temporary_password': 'TempPass123!',
                'permanent_password': 'test123'
            }
        ]
        
        for user in test_users:
            try:
                # Create user
                cognito.admin_create_user(
                    UserPoolId=user_pool_id,
                    Username=user['username'],
                    UserAttributes=[
                        {'Name': 'email', 'Value': user['email']},
                        {'Name': 'email_verified', 'Value': 'true'},
                        {'Name': 'given_name', 'Value': user['given_name']},
                        {'Name': 'family_name', 'Value': user['family_name']}
                    ],
                    TemporaryPassword=user['temporary_password'],
                    MessageAction='SUPPRESS'  # Don't send welcome email
                )
                
                # Set permanent password
                cognito.admin_set_user_password(
                    UserPoolId=user_pool_id,
                    Username=user['username'],
                    Password=user['permanent_password'],
                    Permanent=True
                )
                
                # Confirm user (mark as verified)
                cognito.admin_confirm_sign_up(
                    UserPoolId=user_pool_id,
                    Username=user['username']
                )
                
                print(f"  ✓ Created test user: {user['email']}")
                
            except Exception as e:
                if "UsernameExistsException" in str(e):
                    print(f"  ✓ Test user already exists: {user['email']}")
                else:
                    print(f"  ✗ Failed to create test user {user['email']}: {e}")
    
    def _update_frontend_env(self, user_pool_id, client_id):
        """Update frontend environment file with actual Cognito IDs"""
        env_file = 'frontend/.env.local'
        
        try:
            env_content = f"""# Local development configuration
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID={user_pool_id}
VITE_COGNITO_USER_POOL_CLIENT_ID={client_id}

VITE_API_BASE_URL=http://localhost:4566
VITE_NODE_ENV=development
"""
            
            with open(env_file, 'w') as f:
                f.write(env_content)
            
            print(f"  ✓ Updated {env_file} with Cognito IDs")
            
        except Exception as e:
            print(f"  ⚠ Could not update frontend environment: {e}")

    def create_lambda_functions(self) -> None:
        """Create Lambda functions using actual handler files from the project"""
        lambda_client = self.get_client('lambda')
        account_id = self.get_account_id()
        
        # Lambda function configurations mapping to actual handlers
        lambda_functions = [
            {
                'name': 'tutor-system-auth',
                'handler_path': 'src/lambda_functions/auth/handler.py',
                'handler': 'handler.lambda_handler',
                'description': 'Cognito-based authentication handler',
                'timeout': 30,
                'memory': 256,
                'environment': {
                    'USER_POOL_ID': 'us-east-1_EXAMPLE123',  # Will be updated by Cognito setup
                    'USER_POOL_CLIENT_ID': 'abcdef123456789example'
                }
            },
            {
                'name': 'tutor-system-quiz-engine',
                'handler_path': 'src/lambda_functions/quiz_engine/handler.py',
                'handler': 'handler.lambda_handler',
                'description': 'Quiz session management and question presentation',
                'timeout': 60,
                'memory': 512
            },
            {
                'name': 'tutor-system-answer-evaluation',
                'handler_path': 'src/lambda_functions/answer_evaluation/handler.py',
                'handler': 'handler.lambda_handler',
                'description': 'Semantic answer evaluation using ML models',
                'timeout': 120,
                'memory': 1024,
                'environment': {
                    'MODEL_PATH': './final_similarity_model',
                    'SIMILARITY_THRESHOLD': '0.7'
                }
            },
            {
                'name': 'tutor-system-progress-tracking',
                'handler_path': 'src/lambda_functions/progress_tracking/handler.py',
                'handler': 'handler.lambda_handler',
                'description': 'Progress recording and mastery calculation',
                'timeout': 45,
                'memory': 256
            },
            {
                'name': 'tutor-system-domain-management',
                'handler_path': 'src/lambda_functions/domain_management/handler.py',
                'handler': 'handler.lambda_handler',
                'description': 'CRUD operations for knowledge domains and terms',
                'timeout': 30,
                'memory': 256
            },
            {
                'name': 'tutor-system-batch-upload',
                'handler_path': 'src/lambda_functions/batch_upload/handler.py',
                'handler': 'handler.lambda_handler',
                'description': 'Batch upload validation and processing',
                'timeout': 300,  # 5 minutes for large uploads
                'memory': 512
            }
        ]
        
        for func_config in lambda_functions:
            try:
                # Create deployment package from actual handler file
                zip_content = self._create_lambda_package(func_config['handler_path'])
                
                if zip_content is None:
                    print(f"⚠ Skipping {func_config['name']} - handler file not found")
                    continue
                
                # Prepare environment variables
                environment = {
                    'LOCALSTACK_ENDPOINT': 'http://localhost:4566',
                    'AWS_DEFAULT_REGION': 'us-east-1',
                    'PYTHONPATH': '/var/task:/opt/python'
                }
                
                # Add function-specific environment variables
                if 'environment' in func_config:
                    environment.update(func_config['environment'])
                
                lambda_client.create_function(
                    FunctionName=func_config['name'],
                    Runtime='python3.11',
                    Role=f'arn:aws:iam::{account_id}:role/lambda-role',
                    Handler=func_config['handler'],
                    Code={'ZipFile': zip_content},
                    Description=func_config['description'],
                    Timeout=func_config['timeout'],
                    MemorySize=func_config['memory'],
                    Environment={'Variables': environment},
                    Tags={
                        'Environment': 'development',
                        'Project': 'tutor-system',
                        'ManagedBy': 'LocalStack'
                    }
                )
                print(f"✓ Created Lambda function: {func_config['name']}")
                
            except Exception as e:
                if "ResourceConflictException" in str(e):
                    print(f"✓ Lambda function already exists: {func_config['name']}")
                else:
                    print(f"✗ Failed to create Lambda function {func_config['name']}: {e}")
    
    def _create_lambda_package(self, handler_path: str) -> bytes:
        """Create a deployment package from the actual handler file and dependencies"""
        import zipfile
        import io
        import os
        from pathlib import Path
        
        # Check if handler file exists
        if not os.path.exists(handler_path):
            print(f"Handler file not found: {handler_path}")
            return None
        
        zip_buffer = io.BytesIO()
        
        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add the main handler file
                handler_dir = os.path.dirname(handler_path)
                handler_filename = os.path.basename(handler_path)
                
                # Add handler.py as the main entry point
                zip_file.write(handler_path, 'handler.py')
                
                # Add shared modules (critical for Lambda functions)
                shared_dir = 'src/shared'
                if os.path.exists(shared_dir):
                    for root, dirs, files in os.walk(shared_dir):
                        for file in files:
                            if file.endswith('.py'):
                                file_path = os.path.join(root, file)
                                # Add to shared/ directory in zip
                                arcname = os.path.join('shared', os.path.relpath(file_path, shared_dir))
                                zip_file.write(file_path, arcname)
                
                # Add any additional files from the handler directory
                if os.path.exists(handler_dir):
                    for file in os.listdir(handler_dir):
                        if file.endswith('.py') and file != handler_filename:
                            file_path = os.path.join(handler_dir, file)
                            zip_file.write(file_path, file)
                
                # Add requirements if they exist (for dependencies)
                requirements_path = 'src/lambda_functions/requirements.txt'
                if os.path.exists(requirements_path):
                    zip_file.write(requirements_path, 'requirements.txt')
                
                # Add __init__.py files to make packages importable
                zip_file.writestr('__init__.py', '')
                zip_file.writestr('shared/__init__.py', '')
            
            zip_buffer.seek(0)
            return zip_buffer.getvalue()
            
        except Exception as e:
            print(f"Error creating Lambda package for {handler_path}: {e}")
            return None
    
    def create_vpc_infrastructure(self) -> Dict[str, str]:
        """Create VPC, subnets, and security groups for RDS"""
        print("🌐 Setting up VPC infrastructure...")
        
        ec2_client = self.get_client('ec2')
        
        # VPC configuration
        vpc_cidr = '10.0.0.0/16'
        subnet_cidrs = ['10.0.1.0/24', '10.0.2.0/24']
        availability_zones = ['us-east-1a', 'us-east-1b']
        
        vpc_id = None
        subnet_ids = []
        security_group_id = None
        
        try:
            # Create VPC
            vpc_response = ec2_client.create_vpc(
                CidrBlock=vpc_cidr,
                TagSpecifications=[
                    {
                        'ResourceType': 'vpc',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'tutor-system-vpc'},
                            {'Key': 'Environment', 'Value': 'development'},
                            {'Key': 'Project', 'Value': 'tutor-system'}
                        ]
                    }
                ]
            )
            vpc_id = vpc_response['Vpc']['VpcId']
            print(f"✓ Created VPC: {vpc_id}")
            
            # Enable DNS hostnames and resolution
            ec2_client.modify_vpc_attribute(
                VpcId=vpc_id,
                EnableDnsHostnames={'Value': True}
            )
            ec2_client.modify_vpc_attribute(
                VpcId=vpc_id,
                EnableDnsSupport={'Value': True}
            )
            
            # Create Internet Gateway
            igw_response = ec2_client.create_internet_gateway(
                TagSpecifications=[
                    {
                        'ResourceType': 'internet-gateway',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'tutor-system-igw'},
                            {'Key': 'Environment', 'Value': 'development'}
                        ]
                    }
                ]
            )
            igw_id = igw_response['InternetGateway']['InternetGatewayId']
            
            # Attach Internet Gateway to VPC
            ec2_client.attach_internet_gateway(
                InternetGatewayId=igw_id,
                VpcId=vpc_id
            )
            print(f"✓ Created and attached Internet Gateway: {igw_id}")
            
            # Create subnets in different AZs
            for i, (cidr, az) in enumerate(zip(subnet_cidrs, availability_zones)):
                subnet_response = ec2_client.create_subnet(
                    VpcId=vpc_id,
                    CidrBlock=cidr,
                    AvailabilityZone=az,
                    TagSpecifications=[
                        {
                            'ResourceType': 'subnet',
                            'Tags': [
                                {'Key': 'Name', 'Value': f'tutor-system-subnet-{i+1}'},
                                {'Key': 'Environment', 'Value': 'development'},
                                {'Key': 'Type', 'Value': 'database'}
                            ]
                        }
                    ]
                )
                subnet_id = subnet_response['Subnet']['SubnetId']
                subnet_ids.append(subnet_id)
                print(f"✓ Created subnet: {subnet_id} in {az}")
            
            # Create route table and route to Internet Gateway
            route_table_response = ec2_client.create_route_table(
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        'ResourceType': 'route-table',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'tutor-system-rt'},
                            {'Key': 'Environment', 'Value': 'development'}
                        ]
                    }
                ]
            )
            route_table_id = route_table_response['RouteTable']['RouteTableId']
            
            # Add route to Internet Gateway
            ec2_client.create_route(
                RouteTableId=route_table_id,
                DestinationCidrBlock='0.0.0.0/0',
                GatewayId=igw_id
            )
            
            # Associate subnets with route table
            for subnet_id in subnet_ids:
                ec2_client.associate_route_table(
                    RouteTableId=route_table_id,
                    SubnetId=subnet_id
                )
            
            print(f"✓ Created route table and associated subnets: {route_table_id}")
            
            # Create security group for RDS
            sg_response = ec2_client.create_security_group(
                GroupName='tutor-system-rds-sg',
                Description='Security group for tutor system RDS instance',
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        'ResourceType': 'security-group',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'tutor-system-rds-sg'},
                            {'Key': 'Environment', 'Value': 'development'},
                            {'Key': 'Purpose', 'Value': 'database'}
                        ]
                    }
                ]
            )
            security_group_id = sg_response['GroupId']
            
            # Add inbound rules for PostgreSQL
            ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'IpRanges': [
                            {
                                'CidrIp': vpc_cidr,
                                'Description': 'PostgreSQL access from VPC'
                            }
                        ]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': 'PostgreSQL access for LocalStack development'
                            }
                        ]
                    }
                ]
            )
            print(f"✓ Created security group: {security_group_id}")
            
            return {
                'vpc_id': vpc_id,
                'subnet_ids': subnet_ids,
                'security_group_id': security_group_id,
                'internet_gateway_id': igw_id,
                'route_table_id': route_table_id
            }
            
        except Exception as e:
            if "InvalidVpc.Conflict" in str(e) or "already exists" in str(e).lower():
                print("✓ VPC infrastructure already exists, retrieving existing resources...")
                return self._get_existing_vpc_resources()
            else:
                print(f"✗ Failed to create VPC infrastructure: {e}")
                raise
    
    def _get_existing_vpc_resources(self) -> Dict[str, str]:
        """Get existing VPC resources by tags"""
        ec2_client = self.get_client('ec2')
        
        try:
            # Find VPC by tag
            vpcs = ec2_client.describe_vpcs(
                Filters=[
                    {'Name': 'tag:Name', 'Values': ['tutor-system-vpc']},
                    {'Name': 'tag:Project', 'Values': ['tutor-system']}
                ]
            )
            
            if not vpcs['Vpcs']:
                raise Exception("No existing VPC found with expected tags")
            
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            
            # Find subnets
            subnets = ec2_client.describe_subnets(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'tag:Type', 'Values': ['database']}
                ]
            )
            subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
            
            # Find security group
            security_groups = ec2_client.describe_security_groups(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'tag:Name', 'Values': ['tutor-system-rds-sg']}
                ]
            )
            
            if not security_groups['SecurityGroups']:
                raise Exception("No existing security group found")
            
            security_group_id = security_groups['SecurityGroups'][0]['GroupId']
            
            print(f"✓ Found existing VPC: {vpc_id}")
            print(f"✓ Found existing subnets: {subnet_ids}")
            print(f"✓ Found existing security group: {security_group_id}")
            
            return {
                'vpc_id': vpc_id,
                'subnet_ids': subnet_ids,
                'security_group_id': security_group_id,
                'internet_gateway_id': '',  # Not needed for existing
                'route_table_id': ''  # Not needed for existing
            }
            
        except Exception as e:
            print(f"✗ Failed to retrieve existing VPC resources: {e}")
            raise

    def setup_rds_instance(self) -> None:
        """Setup RDS PostgreSQL instance for Aurora Serverless emulation"""
        print("🗄️  Setting up RDS PostgreSQL instance...")
        
        # First create VPC infrastructure
        vpc_resources = self.create_vpc_infrastructure()
        
        rds_client = self.get_client('rds')
        
        # RDS configuration
        db_instance_identifier = 'tutor-system-db'
        db_name = 'tutor_system'
        master_username = 'tutor_user'
        master_password = 'tutor_password'
        
        try:
            # Create DB subnet group with real subnet IDs
            try:
                rds_client.create_db_subnet_group(
                    DBSubnetGroupName='tutor-system-subnet-group',
                    DBSubnetGroupDescription='Subnet group for tutor system database',
                    SubnetIds=vpc_resources['subnet_ids'],
                )
                print("✓ Created DB subnet group with real subnets")
            except Exception as e:
                if "DBSubnetGroupAlreadyExists" in str(e):
                    print("✓ DB subnet group already exists")
                else:
                    print(f"⚠ DB subnet group creation failed: {e}")
            
            # Create RDS instance with real security group
            try:
                rds_client.create_db_instance(
                    DBInstanceIdentifier=db_instance_identifier,
                    DBInstanceClass='db.t3.micro',
                    Engine='postgres',
                    EngineVersion='15.4',
                    MasterUsername=master_username,
                    MasterUserPassword=master_password,
                    DBName=db_name,
                    AllocatedStorage=20,
                    StorageType='gp2',
                    VpcSecurityGroupIds=[vpc_resources['security_group_id']],
                    DBSubnetGroupName='tutor-system-subnet-group',
                    PubliclyAccessible=True,
                    Tags=[
                        {'Key': 'Environment', 'Value': 'development'},
                        {'Key': 'Project', 'Value': 'tutor-system'}
                    ]
                )
                print(f"✓ Created RDS instance: {db_instance_identifier}")
                
                # Create database secret
                secret_value = {
                    'username': master_username,
                    'password': master_password,
                    'engine': 'postgres',
                    'host': f'{db_instance_identifier}.cluster-xyz.us-east-1.rds.amazonaws.com',
                    'port': 5432,
                    'dbname': db_name
                }
                
                secrets_client = self.get_client('secretsmanager')
                secrets_client.create_secret(
                    Name='tutor-system/database/credentials',
                    Description='RDS database credentials',
                    SecretString=json.dumps(secret_value)
                )
                print("✓ Created database credentials secret")
                
            except Exception as e:
                if "DBInstanceAlreadyExists" in str(e):
                    print(f"✓ RDS instance already exists: {db_instance_identifier}")
                else:
                    print(f"✗ Failed to create RDS instance: {e}")
                    
        except Exception as e:
            print(f"✗ RDS setup failed: {e}")
    
    def setup_all(self) -> bool:
        """Set up all LocalStack resources"""
        if not self.wait_for_localstack():
            return False
        
        print("\n🚀 Setting up LocalStack resources...")
        
        # Initialize account ID early in the setup process
        account_id = self.get_account_id()
        print(f"🔑 Using AWS Account ID: {account_id}")
        
        try:
            # Create VPC infrastructure first (needed for RDS)
            vpc_resources = self.create_vpc_infrastructure()
            print()
            
            self.create_s3_buckets()
            print()
            
            self.create_kms_keys()
            print()
            
            self.create_secrets()
            print()
            
            self.create_cognito_resources()
            print()
            
            self.create_lambda_functions()
            print()
            
            # Setup RDS instance (now uses real VPC resources)
            self.setup_rds_instance()
            print()
            
            print("✅ LocalStack setup completed successfully!")
            print(f"🌐 LocalStack endpoint: {self.endpoint_url}")
            print(f"🔑 AWS Account ID: {account_id}")
            print("� Access LocalStack Web UI at: http://localhost:4566/_localstack/health")
            print("\n🌐 VPC Infrastructure:")
            print(f"   VPC ID: {vpc_resources['vpc_id']}")
            print(f"   Subnet IDs: {', '.join(vpc_resources['subnet_ids'])}")
            print(f"   Security Group ID: {vpc_resources['security_group_id']}")
            print("\n🔐 Test user accounts:")
            print("  admin@example.com / admin123")
            print("  test@example.com / test123")
            print("\n🔄 Please restart the frontend server to pick up new Cognito configuration")
            
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up LocalStack resources"""
        print("🧹 Cleaning up LocalStack resources...")
        
        # This will be handled by stopping the LocalStack container
        print("✅ Cleanup completed (stop LocalStack container to fully clean up)")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LocalStack setup for Tutor System")
    parser.add_argument("--endpoint", default="http://localhost:4566", 
                       help="LocalStack endpoint URL")
    parser.add_argument("--cleanup", action="store_true", 
                       help="Clean up resources instead of creating them")
    
    args = parser.parse_args()
    
    setup = LocalStackSetup(endpoint_url=args.endpoint)
    
    if args.cleanup:
        setup.cleanup()
    else:
        success = setup.setup_all()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()