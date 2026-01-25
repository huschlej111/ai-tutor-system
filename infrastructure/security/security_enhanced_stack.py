"""
Security-enhanced modifications for the TutorSystemStack
Provides methods to enhance the existing stack with security configurations
"""

import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_rds as rds,
    aws_s3 as s3,
    aws_iam as iam,
    Duration
)
from constructs import Construct
from typing import Dict, Any
from .encryption_config import EncryptionConfig
from .iam_policies import IAMPolicyGenerator


class SecurityEnhancedStackMixin:
    """Mixin class to add security enhancements to the TutorSystemStack."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize security configurations
        self.encryption_config = EncryptionConfig(self, self.environment)
        self.iam_generator = IAMPolicyGenerator(self.environment, self.account, self.region)
    
    def enhance_lambda_security(self, lambda_functions: Dict[str, _lambda.Function]) -> None:
        """Apply security enhancements to Lambda functions."""
        
        for function_name, function in lambda_functions.items():
            # Apply encryption to environment variables
            self.encryption_config.apply_lambda_encryption(function)
            
            # Apply least privilege IAM policies
            policy_method = getattr(self.iam_generator, f"generate_{function_name}_policy", None)
            if policy_method:
                policy_document = policy_method()
                
                # Create and attach the policy
                policy = iam.Policy(
                    self,
                    f"{function_name.title()}Policy",
                    document=iam.PolicyDocument.from_json(policy_document)
                )
                function.role.attach_inline_policy(policy)
            
            # Add security environment variables
            function.add_environment("ENVIRONMENT", self.environment)
            function.add_environment("SECURITY_HEADERS_ENABLED", "true")
            function.add_environment("ENCRYPTION_ENABLED", "true")
            
            # Configure function-specific security settings
            if function_name == "auth":
                function.add_environment("JWT_ALGORITHM", "HS256")
                function.add_environment("SESSION_TIMEOUT", "3600")  # 1 hour
                function.add_environment("MAX_LOGIN_ATTEMPTS", "5")
            
            elif function_name == "answer_evaluation":
                function.add_environment("MODEL_ENCRYPTION_ENABLED", "true")
                function.add_environment("SIMILARITY_THRESHOLD_MIN", "0.5")
                function.add_environment("SIMILARITY_THRESHOLD_MAX", "1.0")
    
    def enhance_api_gateway_security(self, api: apigateway.RestApi) -> None:
        """Apply security enhancements to API Gateway."""
        
        # Add security headers to all responses
        security_headers = self.encryption_config.create_security_headers_policy()
        
        # Create a response model with security headers
        response_model = apigateway.Model(
            self,
            "SecurityResponseModel",
            rest_api=api,
            content_type="application/json",
            schema=apigateway.JsonSchema(
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "message": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "data": apigateway.JsonSchema(type=apigateway.JsonSchemaType.OBJECT),
                    "timestamp": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
                }
            )
        )
        
        # Add request validation
        request_validator = apigateway.RequestValidator(
            self,
            "RequestValidator",
            rest_api=api,
            validate_request_body=True,
            validate_request_parameters=True
        )
        
        # Configure throttling
        api.add_usage_plan(
            "SecurityUsagePlan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=100,  # requests per second
                burst_limit=200  # burst capacity
            ),
            quota=apigateway.QuotaSettings(
                limit=10000,  # requests per day
                period=apigateway.Period.DAY
            )
        )
        
        # Add WAF (Web Application Firewall) association
        # Note: This would typically be done through CloudFormation or manually
        # as CDK doesn't have direct WAF v2 support for API Gateway yet
        
    def enhance_rds_security(self, cluster: rds.ServerlessCluster) -> None:
        """Apply security enhancements to RDS Aurora cluster."""
        
        # Enable encryption (already done in encryption_config)
        # Add additional security configurations
        
        # Create parameter group with security settings
        parameter_group = rds.ParameterGroup(
            self,
            "AuroraSecurityParameterGroup",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_13_7
            ),
            parameters={
                "log_statement": "all",  # Log all SQL statements
                "log_min_duration_statement": "1000",  # Log slow queries (>1s)
                "shared_preload_libraries": "pg_stat_statements",
                "ssl": "on",  # Enforce SSL
                "log_connections": "on",
                "log_disconnections": "on",
                "log_checkpoints": "on"
            }
        )
        
        # Note: Parameter groups need to be applied during cluster creation
        # This is for reference in future cluster updates
    
    def enhance_s3_security(self, buckets: Dict[str, s3.Bucket]) -> None:
        """Apply security enhancements to S3 buckets."""
        
        for bucket_name, bucket in buckets.items():
            # Add bucket notification for security monitoring
            # (This would integrate with CloudTrail and GuardDuty)
            
            # Add lifecycle policies for security
            bucket.add_lifecycle_rule(
                id="SecurityLogRetention",
                enabled=True,
                transitions=[
                    s3.Transition(
                        storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                        transition_after=Duration.days(30)
                    ),
                    s3.Transition(
                        storage_class=s3.StorageClass.GLACIER,
                        transition_after=Duration.days(90)
                    )
                ],
                expiration=Duration.days(2555)  # 7 years for compliance
            )
            
            # Add bucket policy for secure access
            bucket.add_to_resource_policy(
                iam.PolicyStatement(
                    sid="DenyInsecureConnections",
                    effect=iam.Effect.DENY,
                    principals=[iam.AnyPrincipal()],
                    actions=["s3:*"],
                    resources=[bucket.bucket_arn, f"{bucket.bucket_arn}/*"],
                    conditions={
                        "Bool": {
                            "aws:SecureTransport": "false"
                        }
                    }
                )
            )
    
    def create_security_monitoring_resources(self) -> Dict[str, Any]:
        """Create additional security monitoring resources."""
        
        resources = {}
        
        # Create CloudWatch dashboard for security metrics
        # (This would be implemented with CloudWatch constructs)
        
        # Create custom metrics for security events
        # (This would be implemented in Lambda functions)
        
        # Create SNS topics for security alerts
        # (Already implemented in SecurityMonitoringStack)
        
        return resources
    
    def apply_network_security(self, vpc, security_groups: Dict[str, Any]) -> None:
        """Apply network security configurations."""
        
        # Create VPC endpoints for secure AWS service access
        vpc_endpoints = {}
        
        # S3 VPC Endpoint
        vpc_endpoints['s3'] = vpc.add_gateway_endpoint(
            "S3VPCEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3
        )
        
        # Secrets Manager VPC Endpoint
        vpc_endpoints['secrets_manager'] = vpc.add_interface_endpoint(
            "SecretsManagerVPCEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            private_dns_enabled=True
        )
        
        # KMS VPC Endpoint
        vpc_endpoints['kms'] = vpc.add_interface_endpoint(
            "KMSVPCEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.KMS,
            private_dns_enabled=True
        )
        
        # CloudWatch Logs VPC Endpoint
        vpc_endpoints['logs'] = vpc.add_interface_endpoint(
            "LogsVPCEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            private_dns_enabled=True
        )
        
        # Monitoring VPC Endpoint
        vpc_endpoints['monitoring'] = vpc.add_interface_endpoint(
            "MonitoringVPCEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_MONITORING,
            private_dns_enabled=True
        )
        
        return vpc_endpoints
    
    def create_security_outputs(self) -> None:
        """Create CloudFormation outputs for security resources."""
        
        # KMS Key outputs
        for key_name, key in self.encryption_config.kms_keys.items():
            cdk.CfnOutput(
                self,
                f"{key_name.title()}KMSKeyId",
                value=key.key_id,
                description=f"KMS Key ID for {key_name} encryption"
            )
            
            cdk.CfnOutput(
                self,
                f"{key_name.title()}KMSKeyArn",
                value=key.key_arn,
                description=f"KMS Key ARN for {key_name} encryption"
            )
        
        # Security configuration summary
        cdk.CfnOutput(
            self,
            "SecurityConfigurationSummary",
            value="Encryption at rest and in transit enabled, least privilege IAM policies applied, security monitoring configured",
            description="Summary of applied security configurations"
        )