"""
Encryption Configuration for Know-It-All Tutor System
Defines encryption at rest and in transit configurations for all AWS services
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_kms as kms,
    aws_s3 as s3,
    aws_rds as rds,
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    RemovalPolicy
)
from constructs import Construct
from typing import Dict, Any, Optional


class EncryptionConfig:
    """Centralized encryption configuration for the tutor system."""
    
    def __init__(self, scope: Construct, environment: str):
        self.scope = scope
        self.environment = environment
        
        # Create KMS keys for different services
        self.kms_keys = self._create_kms_keys()
    
    def _create_kms_keys(self) -> Dict[str, kms.Key]:
        """Create KMS keys for different services with appropriate policies."""
        keys = {}
        
        # General application data encryption key
        keys['application'] = kms.Key(
            self.scope,
            "ApplicationEncryptionKey",
            description=f"Application data encryption key for tutor system - {self.environment}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if self.environment == "production" else RemovalPolicy.DESTROY,
            alias=f"tutor-system/application/{self.environment}"
        )
        
        # Database encryption key
        keys['database'] = kms.Key(
            self.scope,
            "DatabaseEncryptionKey",
            description=f"Database encryption key for Aurora cluster - {self.environment}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,  # Always retain database keys
            alias=f"tutor-system/database/{self.environment}"
        )
        
        # Secrets Manager encryption key
        keys['secrets'] = kms.Key(
            self.scope,
            "SecretsEncryptionKey",
            description=f"Secrets Manager encryption key - {self.environment}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,  # Always retain secrets keys
            alias=f"tutor-system/secrets/{self.environment}"
        )
        
        # CloudTrail logs encryption key
        keys['cloudtrail'] = kms.Key(
            self.scope,
            "CloudTrailEncryptionKey",
            description=f"CloudTrail logs encryption key - {self.environment}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,  # Always retain audit log keys
            alias=f"tutor-system/cloudtrail/{self.environment}"
        )
        
        # Lambda environment variables encryption key
        keys['lambda'] = kms.Key(
            self.scope,
            "LambdaEncryptionKey",
            description=f"Lambda environment variables encryption key - {self.environment}",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY if self.environment == "development" else RemovalPolicy.RETAIN,
            alias=f"tutor-system/lambda/{self.environment}"
        )
        
        return keys
    
    def get_s3_encryption_config(self, bucket_type: str = "application") -> s3.BucketEncryption:
        """Get S3 bucket encryption configuration."""
        if bucket_type == "cloudtrail":
            return s3.BucketEncryption.kms(self.kms_keys['cloudtrail'])
        elif bucket_type == "database":
            return s3.BucketEncryption.kms(self.kms_keys['database'])
        else:
            return s3.BucketEncryption.kms(self.kms_keys['application'])
    
    def get_rds_encryption_config(self) -> Dict[str, Any]:
        """Get RDS encryption configuration."""
        return {
            'storage_encrypted': True,
            'kms_key': self.kms_keys['database']
        }
    
    def get_secrets_manager_encryption_config(self) -> kms.Key:
        """Get Secrets Manager encryption configuration."""
        return self.kms_keys['secrets']
    
    def get_lambda_encryption_config(self) -> kms.Key:
        """Get Lambda environment variables encryption configuration."""
        return self.kms_keys['lambda']
    
    def get_cloudwatch_logs_encryption_config(self) -> kms.Key:
        """Get CloudWatch Logs encryption configuration."""
        return self.kms_keys['application']
    
    def get_cloudtrail_encryption_config(self) -> kms.Key:
        """Get CloudTrail encryption configuration."""
        return self.kms_keys['cloudtrail']
    
    def create_encrypted_s3_bucket(
        self,
        bucket_id: str,
        bucket_name: str,
        bucket_type: str = "application",
        **kwargs
    ) -> s3.Bucket:
        """Create an S3 bucket with proper encryption configuration."""
        
        # Default configuration for encrypted buckets
        default_config = {
            'versioned': True,
            'encryption': self.get_s3_encryption_config(bucket_type),
            'block_public_access': s3.BlockPublicAccess.BLOCK_ALL,
            'enforce_ssl': True,
            'server_access_logs_prefix': 'access-logs/',
            'lifecycle_rules': [
                s3.LifecycleRule(
                    id="DeleteIncompleteMultipartUploads",
                    enabled=True,
                    abort_incomplete_multipart_upload_after=cdk.Duration.days(7)
                )
            ]
        }
        
        # Merge with provided kwargs
        config = {**default_config, **kwargs}
        
        return s3.Bucket(
            self.scope,
            bucket_id,
            bucket_name=bucket_name,
            **config
        )
    
    def create_encrypted_log_group(
        self,
        log_group_id: str,
        log_group_name: str,
        retention: logs.RetentionDays = logs.RetentionDays.ONE_YEAR,
        **kwargs
    ) -> logs.LogGroup:
        """Create a CloudWatch log group with encryption."""
        
        return logs.LogGroup(
            self.scope,
            log_group_id,
            log_group_name=log_group_name,
            encryption_key=self.get_cloudwatch_logs_encryption_config(),
            retention=retention,
            removal_policy=RemovalPolicy.RETAIN if self.environment == "production" else RemovalPolicy.DESTROY,
            **kwargs
        )
    
    def create_encrypted_secret(
        self,
        secret_id: str,
        secret_name: str,
        description: str,
        generate_secret_string: Optional[secretsmanager.SecretStringGenerator] = None,
        enable_rotation: bool = True,
        **kwargs
    ) -> secretsmanager.Secret:
        """Create a secret with proper encryption configuration and rotation."""
        
        config = {
            'secret_name': secret_name,
            'description': description,
            'encryption_key': self.get_secrets_manager_encryption_config(),
            'removal_policy': RemovalPolicy.RETAIN if self.environment == "production" else RemovalPolicy.DESTROY
        }
        
        if generate_secret_string:
            config['generate_secret_string'] = generate_secret_string
        
        # Merge with provided kwargs
        config = {**config, **kwargs}
        
        secret = secretsmanager.Secret(
            self.scope,
            secret_id,
            **config
        )
        
        # Configure automatic rotation based on environment
        if enable_rotation and secret_name in ['database-credentials', 'jwt-secret']:
            rotation_days = self._get_rotation_interval()
            
            # Create rotation configuration
            secret.add_rotation_schedule(
                f"{secret_id}RotationSchedule",
                rotation_lambda=self._get_rotation_lambda(),
                automatically_after=cdk.Duration.days(rotation_days)
            )
        
        return secret
    
    def apply_lambda_encryption(self, lambda_function: _lambda.Function) -> None:
        """Apply encryption configuration to a Lambda function."""
        # Set environment variables encryption
        lambda_function.add_environment("KMS_KEY_ID", self.kms_keys['lambda'].key_id)
        
        # Grant Lambda permission to use the KMS key
        self.kms_keys['lambda'].grant_encrypt_decrypt(lambda_function)
    
    def get_transit_encryption_config(self) -> Dict[str, Any]:
        """Get configuration for encryption in transit."""
        return {
            'api_gateway': {
                'security_policy': 'TLS_1_2',
                'minimum_compression_size': 1024,
                'endpoint_configuration': {
                    'types': ['REGIONAL']  # Regional endpoints support TLS 1.2
                }
            },
            'rds': {
                'require_ssl': True,
                'ssl_mode': 'require'
            },
            'lambda': {
                'reserved_concurrent_executions': None,  # Allow auto-scaling
                'timeout': cdk.Duration.seconds(30),
                'memory_size': 256
            },
            's3': {
                'enforce_ssl': True,
                'cors_configuration': {
                    'allowed_methods': [s3.HttpMethods.GET, s3.HttpMethods.POST, s3.HttpMethods.PUT],
                    'allowed_origins': ['https://*'],  # Only HTTPS origins
                    'allowed_headers': ['*'],
                    'max_age': 3000
                }
            }
        }
    
    def create_security_headers_policy(self) -> Dict[str, str]:
        """Create security headers for API Gateway responses."""
        return {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';",
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
    
    def get_network_security_config(self) -> Dict[str, Any]:
        """Get network security configuration."""
        return {
            'vpc': {
                'enable_dns_hostnames': True,
                'enable_dns_support': True,
                'nat_gateways': 0,  # Use VPC endpoints instead for cost optimization
                'max_azs': 2
            },
            'security_groups': {
                'lambda': {
                    'allow_all_outbound': True,  # Lambda needs outbound access
                    'ingress_rules': []  # No inbound access needed
                },
                'rds': {
                    'allow_all_outbound': False,
                    'ingress_rules': [
                        {
                            'port': 5432,
                            'protocol': 'tcp',
                            'source': 'vpc_cidr'
                        }
                    ]
                }
            },
            'vpc_endpoints': [
                's3',
                'secretsmanager',
                'kms',
                'logs',
                'monitoring'
            ]
        }
    
    def export_encryption_summary(self) -> Dict[str, Any]:
        """Export a summary of encryption configurations."""
        return {
            'kms_keys': {
                name: {
                    'key_id': key.key_id,
                    'key_arn': key.key_arn,
                    'alias': f"tutor-system/{name}/{self.environment}"
                }
                for name, key in self.kms_keys.items()
            },
            'encryption_at_rest': {
                's3_buckets': 'KMS encryption with service-specific keys',
                'rds_aurora': 'KMS encryption with database key',
                'secrets_manager': 'KMS encryption with secrets key',
                'cloudwatch_logs': 'KMS encryption with application key',
                'lambda_env_vars': 'KMS encryption with Lambda key'
            },
            'encryption_in_transit': {
                'api_gateway': 'TLS 1.2 minimum',
                'rds_connections': 'SSL/TLS required',
                's3_access': 'HTTPS enforced',
                'secrets_manager': 'TLS 1.2 via AWS SDK',
                'cloudwatch_logs': 'TLS 1.2 via AWS SDK'
            },
            'security_headers': self.create_security_headers_policy(),
            'compliance': {
                'key_rotation': 'Enabled for all KMS keys',
                'secrets_rotation': f'{self._get_rotation_interval()} days for {self.environment}',
                'access_logging': 'Enabled for all services',
                'monitoring': 'CloudTrail and CloudWatch enabled',
                'backup_encryption': 'All backups encrypted with same keys'
            }
        }
    
    def _get_rotation_interval(self) -> int:
        """Get rotation interval based on environment."""
        if self.environment == "production":
            return 180  # 6 months (approximately 180 days)
        elif self.environment == "staging":
            return 30   # 1 month for staging
        else:
            return 2    # 2 days for development/local
    
    def _get_rotation_lambda(self):
        """Get reference to rotation Lambda function."""
        # This would typically reference an existing Lambda function
        # For now, return None - the actual Lambda ARN would be provided
        # when the rotation schedule is created
        return None
    
    def get_rotation_policy_summary(self) -> Dict[str, Any]:
        """Get summary of rotation policies by environment."""
        return {
            'environment': self.environment,
            'rotation_interval_days': self._get_rotation_interval(),
            'rotation_description': {
                'production': '6 months (180 days) - Industry standard for production systems',
                'staging': '1 month (30 days) - More frequent for testing rotation procedures',
                'development': '2 days - Rapid rotation for development and testing',
                'local': '2 days - Same as development for LocalStack compatibility'
            }.get(self.environment, 'Custom interval'),
            'rotated_secrets': [
                'database-credentials',
                'jwt-secret'
            ],
            'non_rotated_secrets': [
                'ml-model-config',
                'api-keys'  # External API keys managed separately
            ]
        }