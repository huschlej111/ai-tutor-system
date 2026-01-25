#!/usr/bin/env python3
"""
Secrets management setup script for Know-It-All Tutor System.
Configures AWS Secrets Manager with rotation, encryption, and access policies.
"""

import argparse
import boto3
import json
import sys
import time
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError


class SecretsManagementSetup:
    """Sets up comprehensive secrets management for the tutor system."""
    
    def __init__(self, region: str = "us-east-1", environment: str = "development"):
        self.region = region
        self.environment = environment
        
        # Initialize AWS clients
        try:
            self.secrets_client = boto3.client('secretsmanager', region_name=region)
            self.kms_client = boto3.client('kms', region_name=region)
            self.iam_client = boto3.client('iam', region_name=region)
            self.lambda_client = boto3.client('lambda', region_name=region)
            self.sts_client = boto3.client('sts', region_name=region)
        except NoCredentialsError:
            print("❌ AWS credentials not found. Please configure AWS CLI or set environment variables.")
            sys.exit(1)
        
        # Get account ID
        try:
            self.account_id = self.sts_client.get_caller_identity()['Account']
        except ClientError as e:
            print(f"❌ Error getting account ID: {e}")
            sys.exit(1)
        
        self.secret_prefix = f"tutor-system/{self.environment}"
    
    def create_kms_keys(self) -> Dict[str, str]:
        """Create KMS keys for secrets encryption."""
        print("🔐 Creating KMS keys for secrets encryption...")
        
        keys = {}
        
        try:
            # Create secrets encryption key
            key_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "Enable IAM User Permissions",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": f"arn:aws:iam::{self.account_id}:root"
                        },
                        "Action": "kms:*",
                        "Resource": "*"
                    },
                    {
                        "Sid": "Allow Secrets Manager",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "secretsmanager.amazonaws.com"
                        },
                        "Action": [
                            "kms:Decrypt",
                            "kms:GenerateDataKey",
                            "kms:CreateGrant"
                        ],
                        "Resource": "*",
                        "Condition": {
                            "StringEquals": {
                                "kms:ViaService": f"secretsmanager.{self.region}.amazonaws.com"
                            }
                        }
                    }
                ]
            }
            
            response = self.kms_client.create_key(
                Description=f"Secrets Manager encryption key for tutor system - {self.environment}",
                KeyUsage='ENCRYPT_DECRYPT',
                KeySpec='SYMMETRIC_DEFAULT',
                Policy=json.dumps(key_policy),
                Tags=[
                    {'TagKey': 'Environment', 'TagValue': self.environment},
                    {'TagKey': 'Project', 'TagValue': 'know-it-all-tutor'},
                    {'TagKey': 'Purpose', 'TagValue': 'secrets-encryption'}
                ]
            )
            
            key_id = response['KeyMetadata']['KeyId']
            keys['secrets'] = key_id
            
            # Create alias
            alias_name = f"alias/tutor-system/secrets/{self.environment}"
            try:
                self.kms_client.create_alias(
                    AliasName=alias_name,
                    TargetKeyId=key_id
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'AlreadyExistsException':
                    raise
            
            print(f"✅ Created KMS key for secrets: {key_id}")
            
            return keys
            
        except ClientError as e:
            print(f"❌ Error creating KMS keys: {e}")
            return {}
    
    def create_secrets(self, kms_key_id: str) -> Dict[str, str]:
        """Create initial secrets with encryption."""
        print("🔒 Creating encrypted secrets...")
        
        secrets = {}
        
        # Database credentials secret
        try:
            db_secret_name = f"{self.secret_prefix}/database-credentials"
            
            response = self.secrets_client.create_secret(
                Name=db_secret_name,
                Description="Database credentials for tutor system",
                GenerateSecretString={
                    'SecretStringTemplate': '{"username": "tutoruser"}',
                    'GenerateStringKey': 'password',
                    'PasswordLength': 32,
                    'ExcludeCharacters': ' %+~`#$&*()|[]{}:;<>?!\'/@"\\',
                    'RequireEachIncludedType': True
                },
                KmsKeyId=kms_key_id,
                Tags=[
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Project', 'Value': 'know-it-all-tutor'},
                    {'Key': 'Type', 'Value': 'database-credentials'}
                ]
            )
            
            secrets['database'] = response['ARN']
            print(f"✅ Created database credentials secret: {db_secret_name}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                print(f"⚠️  Database credentials secret already exists")
            else:
                print(f"❌ Error creating database secret: {e}")
        
        # JWT secret
        try:
            jwt_secret_name = f"{self.secret_prefix}/jwt-secret"
            
            response = self.secrets_client.create_secret(
                Name=jwt_secret_name,
                Description="JWT signing secret for tutor system",
                GenerateSecretString={
                    'GenerateStringKey': 'secret',
                    'PasswordLength': 64,
                    'ExcludeCharacters': ' %+~`#$&*()|[]{}:;<>?!\'/@"\\',
                    'RequireEachIncludedType': False
                },
                KmsKeyId=kms_key_id,
                Tags=[
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Project', 'Value': 'know-it-all-tutor'},
                    {'Key': 'Type', 'Value': 'jwt-secret'}
                ]
            )
            
            secrets['jwt'] = response['ARN']
            print(f"✅ Created JWT secret: {jwt_secret_name}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                print(f"⚠️  JWT secret already exists")
            else:
                print(f"❌ Error creating JWT secret: {e}")
        
        return secrets
    
    def setup_secrets_rotation(self, secrets: Dict[str, str]) -> bool:
        """Set up automatic secrets rotation."""
        print("🔄 Setting up secrets rotation...")
        
        try:
            # Check if rotation Lambda function exists
            rotation_function_name = f"tutor-system-secrets-rotation-{self.environment}"
            
            try:
                self.lambda_client.get_function(FunctionName=rotation_function_name)
                rotation_lambda_arn = f"arn:aws:lambda:{self.region}:{self.account_id}:function:{rotation_function_name}"
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("⚠️  Rotation Lambda function not found. Deploy the CDK stack first.")
                    return False
                else:
                    raise
            
            # Enable rotation for database credentials
            if 'database' in secrets:
                try:
                    self.secrets_client.rotate_secret(
                        SecretId=secrets['database'],
                        RotationLambdaARN=rotation_lambda_arn,
                        RotationRules={
                            'AutomaticallyAfterDays': 30
                        }
                    )
                    print("✅ Enabled rotation for database credentials (30 days)")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidRequestException':
                        print("⚠️  Database credentials rotation already configured")
                    else:
                        raise
            
            # Enable rotation for JWT secret
            if 'jwt' in secrets:
                try:
                    self.secrets_client.rotate_secret(
                        SecretId=secrets['jwt'],
                        RotationLambdaARN=rotation_lambda_arn,
                        RotationRules={
                            'AutomaticallyAfterDays': 90  # Less frequent for JWT
                        }
                    )
                    print("✅ Enabled rotation for JWT secret (90 days)")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidRequestException':
                        print("⚠️  JWT secret rotation already configured")
                    else:
                        raise
            
            return True
            
        except ClientError as e:
            print(f"❌ Error setting up secrets rotation: {e}")
            return False
    
    def create_access_policies(self) -> Dict[str, str]:
        """Create IAM policies for secrets access."""
        print("🔐 Creating IAM access policies...")
        
        policies = {}
        
        # Lambda functions secrets access policy
        lambda_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret"
                    ],
                    "Resource": [
                        f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:{self.secret_prefix}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "kms:Decrypt"
                    ],
                    "Resource": f"arn:aws:kms:{self.region}:{self.account_id}:key/*",
                    "Condition": {
                        "StringEquals": {
                            "kms:ViaService": f"secretsmanager.{self.region}.amazonaws.com"
                        }
                    }
                }
            ]
        }
        
        try:
            policy_name = f"TutorSystemSecretsAccess-{self.environment}"
            
            response = self.iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(lambda_policy),
                Description=f"Secrets Manager access policy for tutor system Lambda functions - {self.environment}",
                Tags=[
                    {'Key': 'Environment', 'Value': self.environment},
                    {'Key': 'Project', 'Value': 'know-it-all-tutor'}
                ]
            )
            
            policies['lambda_access'] = response['Policy']['Arn']
            print(f"✅ Created Lambda secrets access policy: {policy_name}")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExistsException':
                policies['lambda_access'] = f"arn:aws:iam::{self.account_id}:policy/TutorSystemSecretsAccess-{self.environment}"
                print("⚠️  Lambda secrets access policy already exists")
            else:
                print(f"❌ Error creating Lambda access policy: {e}")
        
        return policies
    
    def validate_secrets_setup(self) -> Dict[str, bool]:
        """Validate secrets management setup."""
        print("🔍 Validating secrets management setup...")
        
        results = {}
        
        # Check KMS key
        try:
            alias_name = f"alias/tutor-system/secrets/{self.environment}"
            self.kms_client.describe_key(KeyId=alias_name)
            results['kms_key'] = True
        except ClientError:
            results['kms_key'] = False
        
        # Check secrets exist
        secret_names = [
            f"{self.secret_prefix}/database-credentials",
            f"{self.secret_prefix}/jwt-secret"
        ]
        
        for secret_name in secret_names:
            try:
                self.secrets_client.describe_secret(SecretId=secret_name)
                results[f"secret_{secret_name.split('/')[-1]}"] = True
            except ClientError:
                results[f"secret_{secret_name.split('/')[-1]}"] = False
        
        # Check rotation configuration
        for secret_name in secret_names:
            try:
                response = self.secrets_client.describe_secret(SecretId=secret_name)
                results[f"rotation_{secret_name.split('/')[-1]}"] = 'RotationEnabled' in response and response['RotationEnabled']
            except ClientError:
                results[f"rotation_{secret_name.split('/')[-1]}"] = False
        
        # Check IAM policy
        try:
            policy_name = f"TutorSystemSecretsAccess-{self.environment}"
            self.iam_client.get_policy(PolicyArn=f"arn:aws:iam::{self.account_id}:policy/{policy_name}")
            results['iam_policy'] = True
        except ClientError:
            results['iam_policy'] = False
        
        # Print validation results
        print("\n📋 Secrets Management Validation Results:")
        for component, status in results.items():
            status_icon = "✅" if status else "❌"
            print(f"   {component}: {status_icon}")
        
        return results
    
    def test_secrets_access(self) -> bool:
        """Test secrets access and decryption."""
        print("🧪 Testing secrets access...")
        
        try:
            # Test database credentials
            db_secret_name = f"{self.secret_prefix}/database-credentials"
            response = self.secrets_client.get_secret_value(SecretId=db_secret_name)
            db_creds = json.loads(response['SecretString'])
            
            if 'username' not in db_creds or 'password' not in db_creds:
                print("❌ Database credentials format invalid")
                return False
            
            print("✅ Database credentials accessible and valid")
            
            # Test JWT secret
            jwt_secret_name = f"{self.secret_prefix}/jwt-secret"
            response = self.secrets_client.get_secret_value(SecretId=jwt_secret_name)
            jwt_data = json.loads(response['SecretString'])
            
            if 'secret' not in jwt_data or len(jwt_data['secret']) < 32:
                print("❌ JWT secret format invalid")
                return False
            
            print("✅ JWT secret accessible and valid")
            
            return True
            
        except ClientError as e:
            print(f"❌ Error testing secrets access: {e}")
            return False
    
    def run_full_setup(self) -> bool:
        """Run the complete secrets management setup."""
        print(f"🚀 Setting up secrets management for environment: {self.environment}")
        print(f"📍 Region: {self.region}")
        print(f"🏢 Account: {self.account_id}")
        print("-" * 60)
        
        success_count = 0
        total_steps = 5
        
        # Step 1: Create KMS keys
        kms_keys = self.create_kms_keys()
        if kms_keys:
            success_count += 1
        
        # Step 2: Create secrets
        if kms_keys:
            secrets = self.create_secrets(kms_keys['secrets'])
            if secrets:
                success_count += 1
        else:
            secrets = {}
        
        # Step 3: Set up rotation
        if secrets and self.setup_secrets_rotation(secrets):
            success_count += 1
        
        # Step 4: Create access policies
        policies = self.create_access_policies()
        if policies:
            success_count += 1
        
        # Step 5: Test access
        if self.test_secrets_access():
            success_count += 1
        
        print(f"\n📊 Setup completed: {success_count}/{total_steps} steps successful")
        
        # Validate setup
        validation_results = self.validate_secrets_setup()
        all_valid = all(validation_results.values())
        
        if all_valid:
            print("\n🎉 Secrets management setup completed successfully!")
            print("🔐 All secrets are encrypted with KMS")
            print("🔄 Automatic rotation is configured")
            print("🔒 Least privilege access policies are in place")
        else:
            print("\n⚠️  Some components may need manual configuration")
            print("📖 Check the CDK deployment and AWS console for details")
        
        return success_count == total_steps and all_valid


def main():
    """Main entry point for the secrets management setup script."""
    parser = argparse.ArgumentParser(
        description="Set up secrets management for Know-It-All Tutor System"
    )
    parser.add_argument(
        "--environment",
        choices=["development", "production"],
        default="development",
        help="Environment to configure (default: development)"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing setup without making changes"
    )
    parser.add_argument(
        "--test-access",
        action="store_true",
        help="Test secrets access and decryption"
    )
    
    args = parser.parse_args()
    
    # Create setup instance
    setup = SecretsManagementSetup(
        region=args.region,
        environment=args.environment
    )
    
    if args.validate_only:
        # Only run validation
        results = setup.validate_secrets_setup()
        success = all(results.values())
        sys.exit(0 if success else 1)
    elif args.test_access:
        # Only test access
        success = setup.test_secrets_access()
        sys.exit(0 if success else 1)
    else:
        # Run full setup
        success = setup.run_full_setup()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()