"""
Main CDK Stack for Know-It-All Tutor System
Defines Lambda functions, API Gateway, Aurora Serverless, and supporting resources
"""
import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    aws_s3 as s3,
    aws_cognito as cognito,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import Dict, Any
from security.encryption_config import EncryptionConfig
from security.iam_policies import IAMPolicyGenerator


class TutorSystemStack(Stack):
    """Main stack for the tutor system infrastructure"""
    
    def __init__(self, scope: Construct, construct_id: str, environment: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self._environment = environment
        
        # Create condition for production environment
        # Support both "prod" and "production" for compatibility
        self.is_production = cdk.CfnCondition(
            self,
            "IsProduction",
            expression=cdk.Fn.condition_or(
                cdk.Fn.condition_equals(environment, "prod"),
                cdk.Fn.condition_equals(environment, "production")
            )
        )
        
        # Initialize security configurations
        self.encryption_config = EncryptionConfig(self, environment)
        self.iam_generator = IAMPolicyGenerator(environment, self.account, self.region)
        
        # Create VPC for Aurora Serverless
        self.vpc = self._create_vpc()
        
        # Create database secrets with encryption
        self.db_secret = self._create_database_secret()
        
        # Create VPC for Aurora Serverless
        self.vpc = self._create_vpc()
        
        # Create Aurora Serverless cluster with encryption
        self.aurora_cluster = self._create_aurora_cluster()
        
        # Create Lambda layers
        self.common_layer = self._create_common_layer()
        self.ml_model_layer = self._create_ml_model_layer()
        
        # Create Lambda functions with security configurations
        self.lambda_functions = self._create_lambda_functions()
        
        # Create Cognito User Pool and User Pool Client (after Lambda functions)
        self.user_pool = self._create_user_pool()
        self.user_pool_client = self._create_user_pool_client()
        
        # Create Cognito User Pool Groups for role-based access control
        self.user_pool_groups = self._create_user_pool_groups()
        
        # Create API Gateway with security headers
        self.api_gateway = self._create_api_gateway()
        
        # Set up API security monitoring
        self._setup_api_security_monitoring()
        
        # Create S3 bucket for artifacts with encryption
        self.artifacts_bucket = self._create_artifacts_bucket()
        
        # Output important values
        self._create_outputs()
    
    @property
    def environment(self) -> str:
        """Get the environment name"""
        return self._environment
    
    def _create_vpc(self) -> ec2.Vpc:
        """Create VPC for Aurora Serverless and Lambda functions"""
        return ec2.Vpc(
            self,
            "TutorSystemVPC",
            max_azs=2,  # Aurora Serverless requires at least 2 AZs
            nat_gateways=0,  # Use VPC endpoints instead for cost optimization
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                )
            ]
        )
    
    def _create_database_secret(self) -> secretsmanager.Secret:
        """Create secret for database credentials"""
        return secretsmanager.Secret(
            self,
            "DatabaseSecret",
            description="Database credentials for tutor system",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "tutoruser"}',
                generate_string_key="password",
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/\"\\",
                password_length=32
            )
        )
    
    def _create_user_pool(self) -> cognito.UserPool:
        """Create Cognito User Pool for authentication"""
        return cognito.UserPool(
            self,
            "TutorSystemUserPool",
            user_pool_name=f"know-it-all-tutor-users-{self.environment}",
            # Sign-in configuration
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            # Password policy
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=Duration.days(7)
            ),
            # Account recovery
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            # Email configuration
            email=cognito.UserPoolEmail.with_cognito(
                reply_to="noreply@know-it-all-tutor.com"
            ),
            # MFA configuration
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=True,
                otp=True
            ),
            # User attributes
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                ),
                given_name=cognito.StandardAttribute(
                    required=False,
                    mutable=True
                ),
                family_name=cognito.StandardAttribute(
                    required=False,
                    mutable=True
                )
            ),
            # Auto verification
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True
            ),
            # User invitation
            user_invitation=cognito.UserInvitationConfig(
                email_subject="Welcome to Know-It-All Tutor!",
                email_body="Hello {username}, your temporary password is {####}",
                sms_message="Your Know-It-All Tutor verification code is {####}"
            ),
            # User verification
            user_verification=cognito.UserVerificationConfig(
                email_subject="Verify your Know-It-All Tutor account",
                email_body="Thank you for signing up! Your verification code is {####}",
                email_style=cognito.VerificationEmailStyle.CODE,
                sms_message="Your Know-It-All Tutor verification code is {####}"
            ),
            # Device tracking
            device_tracking=cognito.DeviceTracking(
                challenge_required_on_new_device=True,
                device_only_remembered_on_user_prompt=False
            ),
            # Advanced security
            advanced_security_mode=cognito.AdvancedSecurityMode.ENFORCED,
            # Lambda triggers
            lambda_triggers=cognito.UserPoolTriggers(
                pre_sign_up=self.lambda_functions["cognito_pre_signup"],
                post_confirmation=self.lambda_functions["cognito_post_confirmation"],
                pre_authentication=self.lambda_functions["cognito_pre_authentication"],
                post_authentication=self.lambda_functions["cognito_post_authentication"]
            ),
            # Deletion protection
            deletion_protection=self.environment == "production",
            removal_policy=RemovalPolicy.DESTROY if self.environment == "development" else RemovalPolicy.RETAIN
        )
    
    def _create_user_pool_client(self) -> cognito.UserPoolClient:
        """Create Cognito User Pool Client for web application"""
        return cognito.UserPoolClient(
            self,
            "TutorSystemUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name=f"know-it-all-tutor-web-client-{self.environment}",
            # Authentication flows
            auth_flows=cognito.AuthFlow(
                user_srp=True,
                user_password=True,  # For migration purposes
                admin_user_password=False,
                custom=False
            ),
            # Token validity
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            # OAuth configuration
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=False
                ),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE
                ],
                callback_urls=[
                    f"https://app.know-it-all-tutor.com/auth/callback",
                    "http://localhost:3000/auth/callback"  # Development
                ],
                logout_urls=[
                    f"https://app.know-it-all-tutor.com/auth/logout",
                    "http://localhost:3000/auth/logout"    # Development
                ]
            ),
            # Security
            generate_secret=False,  # Public client for web applications
            prevent_user_existence_errors=True,
            # Supported identity providers
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ]
        )
    
    def _create_user_pool_groups(self) -> Dict[str, cognito.CfnUserPoolGroup]:
        """Create Cognito User Pool Groups for role-based access control"""
        groups = {}
        
        # Admin group for administrative functions
        groups["admin"] = cognito.CfnUserPoolGroup(
            self,
            "AdminGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="admin",
            description="Administrators with full system access",
            precedence=1,  # Higher precedence (lower number)
            role_arn=self._create_admin_role().role_arn
        )
        
        # Instructor group for content creation and management
        groups["instructor"] = cognito.CfnUserPoolGroup(
            self,
            "InstructorGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="instructor",
            description="Instructors who can create and manage learning content",
            precedence=2,
            role_arn=self._create_instructor_role().role_arn
        )
        
        # Student group for regular users (default)
        groups["student"] = cognito.CfnUserPoolGroup(
            self,
            "StudentGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="student",
            description="Students with access to learning features",
            precedence=3,
            role_arn=self._create_student_role().role_arn
        )
        
        return groups
    
    def _create_admin_role(self) -> iam.Role:
        """Create IAM role for admin users"""
        return iam.Role(
            self,
            "AdminRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.user_pool.user_pool_id
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                }
            ),
            inline_policies={
                "AdminPolicy": iam.PolicyDocument(
                    statements=[
                        # Full access to batch upload operations
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "execute-api:Invoke"
                            ],
                            resources=[
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/POST/batch/*",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/GET/batch/*",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/DELETE/batch/*"
                            ]
                        ),
                        # Access to user management operations
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cognito-idp:AdminGetUser",
                                "cognito-idp:AdminListGroupsForUser",
                                "cognito-idp:AdminAddUserToGroup",
                                "cognito-idp:AdminRemoveUserFromGroup",
                                "cognito-idp:ListUsers"
                            ],
                            resources=[self.user_pool.user_pool_arn]
                        )
                    ]
                )
            }
        )
    
    def _create_instructor_role(self) -> iam.Role:
        """Create IAM role for instructor users"""
        return iam.Role(
            self,
            "InstructorRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.user_pool.user_pool_id
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                }
            ),
            inline_policies={
                "InstructorPolicy": iam.PolicyDocument(
                    statements=[
                        # Access to content creation and batch upload
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "execute-api:Invoke"
                            ],
                            resources=[
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/POST/batch/validate",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/POST/batch/upload",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/GET/batch/history"
                            ]
                        )
                    ]
                )
            }
        )
    
    def _create_student_role(self) -> iam.Role:
        """Create IAM role for student users"""
        return iam.Role(
            self,
            "StudentRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.user_pool.user_pool_id
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                }
            ),
            inline_policies={
                "StudentPolicy": iam.PolicyDocument(
                    statements=[
                        # Standard learning access (domains, quiz, progress)
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "execute-api:Invoke"
                            ],
                            resources=[
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/GET/domains*",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/POST/domains",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/PUT/domains/*",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/DELETE/domains/*",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/*/quiz/*",
                                f"arn:aws:execute-api:{self.region}:{self.account}:*/*/*/progress/*"
                            ]
                        )
                    ]
                )
            }
        )
    
    def _create_aurora_cluster(self) -> rds.ServerlessCluster:
        """Create Aurora Serverless PostgreSQL cluster"""
        # Create security group for Aurora
        aurora_sg = ec2.SecurityGroup(
            self,
            "AuroraSecurityGroup",
            vpc=self.vpc,
            description="Security group for Aurora Serverless cluster",
            allow_all_outbound=False
        )
        
        # Allow inbound connections from Lambda functions
        aurora_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5432),
            description="Allow PostgreSQL connections from VPC"
        )
        
        return rds.ServerlessCluster(
            self,
            "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_13_7
            ),
            credentials=rds.Credentials.from_secret(self.db_secret),
            default_database_name="tutor_system",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[aurora_sg],
            scaling=rds.ServerlessScalingOptions(
                auto_pause=Duration.minutes(5 if self.environment == "development" else 15),
                min_capacity=rds.AuroraCapacityUnit.ACU_2,
                max_capacity=rds.AuroraCapacityUnit.ACU_4 if self.environment == "development" else rds.AuroraCapacityUnit.ACU_8
            ),
            deletion_protection=self.environment == "production",
            removal_policy=RemovalPolicy.DESTROY if self.environment == "development" else RemovalPolicy.RETAIN
        )
    
    def _create_common_layer(self) -> _lambda.LayerVersion:
        """Create Lambda layer for common utilities"""
        return _lambda.LayerVersion(
            self,
            "CommonUtilitiesLayer",
            code=_lambda.Code.from_asset("../src/shared"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Common utilities for tutor system Lambda functions"
        )
    
    def _create_ml_model_layer(self) -> _lambda.LayerVersion:
        """Create Lambda layer for ML model"""
        return _lambda.LayerVersion(
            self,
            "MLModelLayer",
            code=_lambda.Code.from_asset("../final_similarity_model"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Sentence transformer model for answer evaluation"
        )
    
    def _create_lambda_functions(self) -> Dict[str, _lambda.Function]:
        """Create all Lambda functions"""
        functions = {}
        
        # Common environment variables
        common_env = {
            "ENVIRONMENT": self.environment,
            "STAGE": self.environment,  # Add STAGE for environment-aware auth
            "AURORA_ENDPOINT": self.aurora_cluster.cluster_endpoint.hostname,
            "AURORA_PORT": "5432",
            "AURORA_DATABASE": "tutor_system",
            "DB_SECRET_NAME": self.db_secret.secret_name,
            "USER_POOL_ID": self.user_pool.user_pool_id,
            "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
            "AWS_REGION": self.region
        }
        
        # Common Lambda configuration
        common_config = {
            "runtime": _lambda.Runtime.PYTHON_3_11,
            "timeout": Duration.seconds(30),
            "memory_size": 256,
            "environment": common_env,
            "layers": [self.common_layer],
            "vpc": self.vpc,
            "vpc_subnets": ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        }
        
        # Authentication function
        functions["auth"] = _lambda.Function(
            self,
            "AuthFunction",
            code=_lambda.Code.from_asset("../src/lambda_functions/auth"),
            handler="handler.lambda_handler",
            **common_config
        )
        
        # Domain management function
        functions["domain_management"] = _lambda.Function(
            self,
            "DomainManagementFunction",
            code=_lambda.Code.from_asset("../src/lambda_functions/domain_management"),
            handler="handler.lambda_handler",
            **common_config
        )
        
        # Quiz engine function
        functions["quiz_engine"] = _lambda.Function(
            self,
            "QuizEngineFunction",
            code=_lambda.Code.from_asset("../src/lambda_functions/quiz_engine"),
            handler="handler.lambda_handler",
            **common_config
        )
        
        # Answer evaluation function (with ML model layer)
        answer_eval_config = common_config.copy()
        answer_eval_config["layers"].append(self.ml_model_layer)
        answer_eval_config["memory_size"] = 512  # More memory for ML model
        answer_eval_config["timeout"] = Duration.seconds(60)
        answer_eval_config["environment"]["MODEL_PATH"] = "/opt/final_similarity_model"
        
        functions["answer_evaluation"] = _lambda.Function(
            self,
            "AnswerEvaluationFunction",
            code=_lambda.Code.from_asset("../src/lambda_functions/answer_evaluation"),
            handler="handler.lambda_handler",
            **answer_eval_config
        )
        
        # Progress tracking function
        functions["progress_tracking"] = _lambda.Function(
            self,
            "ProgressTrackingFunction",
            code=_lambda.Code.from_asset("../src/lambda_functions/progress_tracking"),
            handler="handler.lambda_handler",
            **common_config
        )
        
        # Batch upload function
        functions["batch_upload"] = _lambda.Function(
            self,
            "BatchUploadFunction",
            code=_lambda.Code.from_asset("../src/lambda_functions/batch_upload"),
            handler="handler.lambda_handler",
            **common_config
        )
        
        # Database migration function
        functions["db_migration"] = _lambda.Function(
            self,
            "DatabaseMigrationFunction",
            code=_lambda.Code.from_asset("../src/lambda_functions/db_migration"),
            handler="handler.lambda_handler",
            **common_config
        )
        
        # Cognito trigger functions (no VPC needed for triggers)
        trigger_config = {
            "runtime": _lambda.Runtime.PYTHON_3_11,
            "timeout": Duration.seconds(30),
            "memory_size": 256,
            "environment": common_env,
            "layers": [self.common_layer]
        }
        
        functions["cognito_pre_signup"] = _lambda.Function(
            self,
            "CognitoPreSignupTrigger",
            code=_lambda.Code.from_asset("../src/lambda_functions/cognito_triggers"),
            handler="pre_signup.lambda_handler",
            **trigger_config
        )
        
        functions["cognito_post_confirmation"] = _lambda.Function(
            self,
            "CognitoPostConfirmationTrigger",
            code=_lambda.Code.from_asset("../src/lambda_functions/cognito_triggers"),
            handler="post_confirmation.lambda_handler",
            **trigger_config
        )
        
        functions["cognito_pre_authentication"] = _lambda.Function(
            self,
            "CognitoPreAuthenticationTrigger",
            code=_lambda.Code.from_asset("../src/lambda_functions/cognito_triggers"),
            handler="pre_authentication.lambda_handler",
            **trigger_config
        )
        
        functions["cognito_post_authentication"] = _lambda.Function(
            self,
            "CognitoPostAuthenticationTrigger",
            code=_lambda.Code.from_asset("../src/lambda_functions/cognito_triggers"),
            handler="post_authentication.lambda_handler",
            **trigger_config
        )
        
        # Grant permissions to all functions
        for function in functions.values():
            # Grant access to secrets
            self.db_secret.grant_read(function)
            
            # Grant VPC access
            function.add_to_role_policy(
                iam.PolicyStatement(
                    actions=[
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface"
                    ],
                    resources=["*"]
                )
            )
        
        # Grant Cognito permission to invoke trigger functions
        for trigger_name in ["cognito_pre_signup", "cognito_post_confirmation", 
                           "cognito_pre_authentication", "cognito_post_authentication"]:
            if trigger_name in functions:
                functions[trigger_name].add_permission(
                    f"CognitoInvoke{trigger_name}",
                    principal=iam.ServicePrincipal("cognito-idp.amazonaws.com"),
                    action="lambda:InvokeFunction"
                )
        
        return functions
    
    def _create_api_gateway(self) -> apigateway.RestApi:
        """Create API Gateway with Lambda integrations"""
        api = apigateway.RestApi(
            self,
            "TutorSystemAPI",
            rest_api_name=f"tutor-system-api-{self.environment}",
            description=f"API for Know-It-All Tutor System - {self.environment}",
            # Enhanced CORS configuration for frontend integration
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["https://app.know-it-all-tutor.com", "http://localhost:3000"] if self.environment == "production" 
                           else apigateway.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=[
                    "Content-Type", 
                    "Authorization", 
                    "X-Amz-Date", 
                    "X-Api-Key", 
                    "X-Amz-Security-Token",
                    "X-Requested-With",
                    "Accept",
                    "Origin"
                ],
                allow_credentials=True,
                max_age=Duration.hours(1)
            ),
            # Request/response transformation settings
            default_method_options=apigateway.MethodOptions(
                throttling=apigateway.ThrottleSettings(
                    rate_limit=1000 if self.environment == "production" else 100,
                    burst_limit=2000 if self.environment == "production" else 200
                ),
                # API key required for admin endpoints
                api_key_required=False  # Will be set per method for admin endpoints
            ),
            # Binary media types for file uploads
            binary_media_types=["application/json", "multipart/form-data"],
            # Minimum compression size
            minimum_compression_size=1024,
            # API Gateway policy for additional security
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        principals=[iam.AnyPrincipal()],
                        actions=["execute-api:Invoke"],
                        resources=["*"],
                        conditions={
                            "IpAddress": {
                                "aws:SourceIp": ["0.0.0.0/0"]  # Allow all IPs in development
                            }
                        } if self.environment == "development" else {}
                    )
                ]
            ) if self.environment == "development" else None
        )
        
        # Create Cognito User Pool Authorizer (conditionally for production)
        # Only create if we're in production environment
        if self.environment in ["prod", "production"]:
            self.cognito_authorizer = apigateway.CognitoUserPoolsAuthorizer(
                self,
                "CognitoUserPoolAuthorizer",
                cognito_user_pools=[self.user_pool],
                authorizer_name="CognitoUserPoolAuthorizer",
                identity_source="method.request.header.Authorization",
                results_cache_ttl=Duration.minutes(5)
            )
        else:
            # For development/local, create a placeholder that won't be used
            self.cognito_authorizer = None
        
        # Create API resources and methods
        self._create_api_routes(api)
        
        # Add request/response models for validation
        self._create_api_models(api)
        
        # Create API keys and usage plans for admin access
        self._create_api_keys_and_usage_plans(api)
        
        return api
    
    def _create_api_keys_and_usage_plans(self, api: apigateway.RestApi):
        """Create API keys and usage plans for rate limiting and admin access"""
        
        # Create API key for admin operations
        admin_api_key = api.add_api_key(
            "AdminAPIKey",
            api_key_name=f"tutor-system-admin-key-{self.environment}",
            description="API key for administrative operations"
        )
        
        # Create usage plan for admin operations
        admin_usage_plan = api.add_usage_plan(
            "AdminUsagePlan",
            name=f"tutor-system-admin-plan-{self.environment}",
            description="Usage plan for administrative operations",
            throttle=apigateway.ThrottleSettings(
                rate_limit=500,  # Higher rate limit for admin operations
                burst_limit=1000
            ),
            quota=apigateway.QuotaSettings(
                limit=10000,  # 10,000 requests per day for admin
                period=apigateway.Period.DAY
            ),
            api_stages=[
                apigateway.UsagePlanPerApiStage(
                    api=api,
                    stage=api.deployment_stage
                )
            ]
        )
        
        # Associate API key with usage plan
        admin_usage_plan.add_api_key(admin_api_key)
        
        # Create usage plan for regular users
        user_usage_plan = api.add_usage_plan(
            "UserUsagePlan",
            name=f"tutor-system-user-plan-{self.environment}",
            description="Usage plan for regular user operations",
            throttle=apigateway.ThrottleSettings(
                rate_limit=100,  # Standard rate limit for users
                burst_limit=200
            ),
            quota=apigateway.QuotaSettings(
                limit=1000,  # 1,000 requests per day for regular users
                period=apigateway.Period.DAY
            ),
            api_stages=[
                apigateway.UsagePlanPerApiStage(
                    api=api,
                    stage=api.deployment_stage
                )
            ]
        )
    
    def _create_api_models(self, api: apigateway.RestApi):
        """Create API Gateway models for request/response validation"""
        
        # User registration model
        user_registration_model = api.add_model(
            "UserRegistrationModel",
            content_type="application/json",
            model_name="UserRegistration",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="User Registration",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "email": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        format="email"
                    ),
                    "password": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        min_length=8
                    ),
                    "first_name": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        max_length=50
                    ),
                    "last_name": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        max_length=50
                    )
                },
                required=["email", "password"]
            )
        )
        
        # User login model
        user_login_model = api.add_model(
            "UserLoginModel",
            content_type="application/json",
            model_name="UserLogin",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="User Login",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "email": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        format="email"
                    ),
                    "password": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING
                    )
                },
                required=["email", "password"]
            )
        )
        
        # Domain creation model
        domain_creation_model = api.add_model(
            "DomainCreationModel",
            content_type="application/json",
            model_name="DomainCreation",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="Domain Creation",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "name": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        min_length=1,
                        max_length=100
                    ),
                    "description": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        max_length=500
                    ),
                    "terms": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.ARRAY,
                        items=apigateway.JsonSchema(
                            type=apigateway.JsonSchemaType.OBJECT,
                            properties={
                                "term": apigateway.JsonSchema(
                                    type=apigateway.JsonSchemaType.STRING,
                                    min_length=1,
                                    max_length=200
                                ),
                                "definition": apigateway.JsonSchema(
                                    type=apigateway.JsonSchemaType.STRING,
                                    min_length=1,
                                    max_length=1000
                                )
                            },
                            required=["term", "definition"]
                        )
                    )
                },
                required=["name", "terms"]
            )
        )
        
        # Quiz answer model
        quiz_answer_model = api.add_model(
            "QuizAnswerModel",
            content_type="application/json",
            model_name="QuizAnswer",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="Quiz Answer",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "session_id": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING
                    ),
                    "answer": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING,
                        min_length=1,
                        max_length=1000
                    )
                },
                required=["session_id", "answer"]
            )
        )
        
        # Batch upload model
        batch_upload_model = api.add_model(
            "BatchUploadModel",
            content_type="application/json",
            model_name="BatchUpload",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="Batch Upload",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "domains": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.ARRAY,
                        items=apigateway.JsonSchema(
                            type=apigateway.JsonSchemaType.OBJECT,
                            properties={
                                "name": apigateway.JsonSchema(
                                    type=apigateway.JsonSchemaType.STRING,
                                    min_length=1,
                                    max_length=100
                                ),
                                "description": apigateway.JsonSchema(
                                    type=apigateway.JsonSchemaType.STRING,
                                    max_length=500
                                ),
                                "terms": apigateway.JsonSchema(
                                    type=apigateway.JsonSchemaType.ARRAY,
                                    items=apigateway.JsonSchema(
                                        type=apigateway.JsonSchemaType.OBJECT,
                                        properties={
                                            "term": apigateway.JsonSchema(
                                                type=apigateway.JsonSchemaType.STRING,
                                                min_length=1,
                                                max_length=200
                                            ),
                                            "definition": apigateway.JsonSchema(
                                                type=apigateway.JsonSchemaType.STRING,
                                                min_length=1,
                                                max_length=1000
                                            )
                                        },
                                        required=["term", "definition"]
                                    )
                                )
                            },
                            required=["name", "terms"]
                        )
                    )
                },
                required=["domains"]
            )
        )
        
        # Error response model
        error_response_model = api.add_model(
            "ErrorResponseModel",
            content_type="application/json",
            model_name="ErrorResponse",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="Error Response",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "error": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING
                    ),
                    "message": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING
                    ),
                    "timestamp": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.STRING
                    )
                },
                required=["error", "message"]
            )
        )
    
    def _create_protected_method(self, resource: apigateway.Resource, http_method: str, 
                               lambda_function: _lambda.Function, integration_options: dict, 
                               method_options: dict) -> apigateway.Method:
        """Create a method with conditional authorization based on environment"""
        
        # For production environments, use Cognito authorizer
        if self.environment in ["prod", "production"] and self.cognito_authorizer:
            method_options_with_auth = method_options.copy()
            method_options_with_auth["authorizer"] = self.cognito_authorizer
            
            return resource.add_method(
                http_method,
                apigateway.LambdaIntegration(lambda_function, **integration_options),
                **method_options_with_auth
            )
        else:
            # For development/local, no authorization required
            return resource.add_method(
                http_method,
                apigateway.LambdaIntegration(lambda_function, **integration_options),
                **method_options
            )
    
    def _create_api_routes(self, api: apigateway.RestApi):
        """Create API Gateway routes and integrations"""
        
        # Common integration options for better error handling and security
        integration_options = apigateway.IntegrationOptions(
            timeout=Duration.seconds(29),  # API Gateway max timeout
            passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_MATCH,
            # Request size validation
            request_parameters={
                "integration.request.header.X-Request-Size": "context.requestLength"
            },
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization'",
                        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'",
                        "method.response.header.Strict-Transport-Security": "'max-age=31536000; includeSubDomains; preload'",
                        "method.response.header.X-Content-Type-Options": "'nosniff'",
                        "method.response.header.X-Frame-Options": "'DENY'",
                        "method.response.header.X-XSS-Protection": "'1; mode=block'",
                        "method.response.header.Referrer-Policy": "'strict-origin-when-cross-origin'"
                    }
                ),
                apigateway.IntegrationResponse(
                    status_code="400",
                    selection_pattern="4\\d{2}",
                    response_templates={
                        "application/json": '{"error": "Bad Request", "message": $input.json(\'$.errorMessage\'), "timestamp": "$context.requestTime"}'
                    },
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Strict-Transport-Security": "'max-age=31536000; includeSubDomains; preload'",
                        "method.response.header.X-Content-Type-Options": "'nosniff'"
                    }
                ),
                apigateway.IntegrationResponse(
                    status_code="413",
                    selection_pattern="Request Entity Too Large",
                    response_templates={
                        "application/json": '{"error": "Request Entity Too Large", "message": "Request body exceeds maximum size limit", "timestamp": "$context.requestTime"}'
                    }
                ),
                apigateway.IntegrationResponse(
                    status_code="429",
                    selection_pattern="Too Many Requests",
                    response_templates={
                        "application/json": '{"error": "Too Many Requests", "message": "Rate limit exceeded", "timestamp": "$context.requestTime"}'
                    }
                ),
                apigateway.IntegrationResponse(
                    status_code="500",
                    selection_pattern="5\\d{2}",
                    response_templates={
                        "application/json": '{"error": "Internal Server Error", "message": "An unexpected error occurred", "timestamp": "$context.requestTime"}'
                    }
                )
            ]
        )
        
        # Common method options for consistent responses and security
        method_options = apigateway.MethodOptions(
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True,
                        "method.response.header.Strict-Transport-Security": True,
                        "method.response.header.X-Content-Type-Options": True,
                        "method.response.header.X-Frame-Options": True,
                        "method.response.header.X-XSS-Protection": True,
                        "method.response.header.Referrer-Policy": True
                    }
                ),
                apigateway.MethodResponse(status_code="400"),
                apigateway.MethodResponse(status_code="401"),
                apigateway.MethodResponse(status_code="403"),
                apigateway.MethodResponse(status_code="404"),
                apigateway.MethodResponse(status_code="413"),  # Request Entity Too Large
                apigateway.MethodResponse(status_code="429"),  # Too Many Requests
                apigateway.MethodResponse(status_code="500")
            ],
            # Request validation
            request_validator=api.add_request_validator(
                "RequestValidator",
                validate_request_body=True,
                validate_request_parameters=True
            )
        )
        
        # Auth routes (public - no authorization needed)
        auth_resource = api.root.add_resource("auth")
        
        # User registration
        register_resource = auth_resource.add_resource("register")
        register_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                self.lambda_functions["auth"],
                **integration_options.__dict__
            ),
            **method_options.__dict__
        )
        
        # User login
        login_resource = auth_resource.add_resource("login")
        login_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                self.lambda_functions["auth"],
                **integration_options.__dict__
            ),
            **method_options.__dict__
        )
        
        # User logout (protected)
        logout_resource = auth_resource.add_resource("logout")
        self._create_protected_method(
            logout_resource, 
            "POST", 
            self.lambda_functions["auth"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Token validation (protected)
        validate_resource = auth_resource.add_resource("validate")
        self._create_protected_method(
            validate_resource, 
            "GET", 
            self.lambda_functions["auth"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Additional auth endpoints for Cognito
        confirm_resource = auth_resource.add_resource("confirm")
        confirm_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                self.lambda_functions["auth"],
                **integration_options.__dict__
            ),
            **method_options.__dict__
        )
        
        resend_resource = auth_resource.add_resource("resend-confirmation")
        resend_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                self.lambda_functions["auth"],
                **integration_options.__dict__
            ),
            **method_options.__dict__
        )
        
        forgot_password_resource = auth_resource.add_resource("forgot-password")
        forgot_password_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                self.lambda_functions["auth"],
                **integration_options.__dict__
            ),
            **method_options.__dict__
        )
        
        confirm_forgot_resource = auth_resource.add_resource("confirm-forgot-password")
        confirm_forgot_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(
                self.lambda_functions["auth"],
                **integration_options.__dict__
            ),
            **method_options.__dict__
        )
        
        change_password_resource = auth_resource.add_resource("change-password")
        self._create_protected_method(
            change_password_resource, 
            "POST", 
            self.lambda_functions["auth"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Domain routes (protected - require authorization)
        domains_resource = api.root.add_resource("domains")
        
        # List domains
        self._create_protected_method(
            domains_resource, 
            "GET", 
            self.lambda_functions["domain_management"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Create domain
        self._create_protected_method(
            domains_resource, 
            "POST", 
            self.lambda_functions["domain_management"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Domain-specific operations
        domain_resource = domains_resource.add_resource("{domainId}")
        
        # Get domain
        self._create_protected_method(
            domain_resource, 
            "GET", 
            self.lambda_functions["domain_management"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Update domain
        self._create_protected_method(
            domain_resource, 
            "PUT", 
            self.lambda_functions["domain_management"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Delete domain
        self._create_protected_method(
            domain_resource, 
            "DELETE", 
            self.lambda_functions["domain_management"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Domain terms operations
        terms_resource = domain_resource.add_resource("terms")
        self._create_protected_method(
            terms_resource, 
            "GET", 
            self.lambda_functions["domain_management"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        self._create_protected_method(
            terms_resource, 
            "POST", 
            self.lambda_functions["domain_management"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Quiz routes (protected - require authorization)
        quiz_resource = api.root.add_resource("quiz")
        
        # Start quiz session
        start_quiz_resource = quiz_resource.add_resource("start")
        self._create_protected_method(
            start_quiz_resource, 
            "POST", 
            self.lambda_functions["quiz_engine"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Submit answer
        answer_resource = quiz_resource.add_resource("answer")
        self._create_protected_method(
            answer_resource, 
            "POST", 
            self.lambda_functions["quiz_engine"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Get current question
        question_resource = quiz_resource.add_resource("question")
        self._create_protected_method(
            question_resource, 
            "GET", 
            self.lambda_functions["quiz_engine"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Quiz session operations
        session_resource = quiz_resource.add_resource("session").add_resource("{sessionId}")
        
        # Get session status
        self._create_protected_method(
            session_resource, 
            "GET", 
            self.lambda_functions["quiz_engine"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Pause/resume session
        self._create_protected_method(
            session_resource, 
            "PUT", 
            self.lambda_functions["quiz_engine"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Complete session
        self._create_protected_method(
            session_resource, 
            "DELETE", 
            self.lambda_functions["quiz_engine"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Answer evaluation routes (internal - used by quiz engine)
        evaluation_resource = api.root.add_resource("evaluation")
        self._create_protected_method(
            evaluation_resource, 
            "POST", 
            self.lambda_functions["answer_evaluation"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Progress routes (protected - require authorization)
        progress_resource = api.root.add_resource("progress")
        
        # Get progress dashboard
        dashboard_resource = progress_resource.add_resource("dashboard")
        self._create_protected_method(
            dashboard_resource, 
            "GET", 
            self.lambda_functions["progress_tracking"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Record progress
        record_resource = progress_resource.add_resource("record")
        self._create_protected_method(
            record_resource, 
            "POST", 
            self.lambda_functions["progress_tracking"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Get domain-specific progress
        domain_progress_resource = progress_resource.add_resource("domain").add_resource("{domainId}")
        self._create_protected_method(
            domain_progress_resource, 
            "GET", 
            self.lambda_functions["progress_tracking"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Batch upload routes (protected - require authorization and API key for admin functions)
        batch_resource = api.root.add_resource("batch")
        
        # Validate batch upload (instructor/admin access)
        validate_resource = batch_resource.add_resource("validate")
        if self.environment in ["prod", "production"] and self.cognito_authorizer:
            validate_resource.add_method(
                "POST",
                apigateway.LambdaIntegration(
                    self.lambda_functions["batch_upload"],
                    **integration_options.__dict__
                ),
                authorizer=self.cognito_authorizer,
                method_options=apigateway.MethodOptions(
                    **method_options.__dict__,
                    api_key_required=True  # Require API key for batch operations
                )
            )
        else:
            validate_resource.add_method(
                "POST",
                apigateway.LambdaIntegration(
                    self.lambda_functions["batch_upload"],
                    **integration_options.__dict__
                ),
                method_options=apigateway.MethodOptions(
                    **method_options.__dict__,
                    api_key_required=True  # Require API key for batch operations
                )
            )
        
        # Execute batch upload (instructor/admin access)
        upload_resource = batch_resource.add_resource("upload")
        if self.environment in ["prod", "production"] and self.cognito_authorizer:
            upload_resource.add_method(
                "POST",
                apigateway.LambdaIntegration(
                    self.lambda_functions["batch_upload"],
                    **integration_options.__dict__
                ),
                authorizer=self.cognito_authorizer,
                method_options=apigateway.MethodOptions(
                    **method_options.__dict__,
                    api_key_required=True  # Require API key for batch operations
                )
            )
        else:
            upload_resource.add_method(
                "POST",
                apigateway.LambdaIntegration(
                    self.lambda_functions["batch_upload"],
                    **integration_options.__dict__
                ),
                method_options=apigateway.MethodOptions(
                    **method_options.__dict__,
                    api_key_required=True  # Require API key for batch operations
                )
            )
        
        # Get upload history (instructor/admin access)
        history_resource = batch_resource.add_resource("history")
        self._create_protected_method(
            history_resource, 
            "GET", 
            self.lambda_functions["batch_upload"], 
            integration_options.__dict__, 
            method_options.__dict__
        )
        
        # Health check endpoint (public)
        health_resource = api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": '{"status": "healthy", "timestamp": "$context.requestTime"}'
                        }
                    )
                ],
                passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                request_templates={
                    "application/json": '{"statusCode": 200}'
                }
            ),
            method_responses=[
                apigateway.MethodResponse(status_code="200")
            ]
        )
    
    def _create_artifacts_bucket(self) -> s3.Bucket:
        """Create S3 bucket for deployment artifacts"""
        return s3.Bucket(
            self,
            "ArtifactsBucket",
            bucket_name=f"tutor-system-artifacts-{self.environment}-{self.account}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY if self.environment == "development" else RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    enabled=True,
                    noncurrent_version_expiration=Duration.days(30)
                )
            ]
        )
    
    def _create_outputs(self):
        """Create CloudFormation outputs"""
        cdk.CfnOutput(
            self,
            "APIGatewayURL",
            value=self.api_gateway.url,
            description="API Gateway URL"
        )
        
        cdk.CfnOutput(
            self,
            "AuroraEndpoint",
            value=self.aurora_cluster.cluster_endpoint.hostname,
            description="Aurora Serverless cluster endpoint"
        )
        
        cdk.CfnOutput(
            self,
            "DatabaseSecretArn",
            value=self.db_secret.secret_arn,
            description="Database credentials secret ARN"
        )
        

        
        cdk.CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID"
        )
        
        cdk.CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID"
        )
        
        cdk.CfnOutput(
            self,
            "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            description="Cognito User Pool ARN"
        )
        
        # Only output authorizer ARN if it exists (production environment)
        if self.cognito_authorizer:
            cdk.CfnOutput(
                self,
                "CognitoAuthorizerArn",
                value=self.cognito_authorizer.authorizer_arn,
                description="Cognito User Pool Authorizer ARN"
            )
    
    def _setup_api_security_monitoring(self):
        """Set up comprehensive API security monitoring and alerting"""
        
        # Import additional CDK modules needed for monitoring
        from aws_cdk import (
            aws_logs as logs,
            aws_cloudwatch as cloudwatch,
            aws_sns as sns,
            aws_cloudwatch_actions as cloudwatch_actions,
            aws_logs_destinations as logs_destinations
        )
        
        # Create CloudWatch Log Group for API Gateway access logs
        api_log_group = logs.LogGroup(
            self,
            "APIGatewayAccessLogs",
            log_group_name=f"/aws/apigateway/tutor-system-{self.environment}",
            retention=logs.RetentionDays.ONE_MONTH if self.environment == "development" else logs.RetentionDays.THREE_MONTHS,
            removal_policy=RemovalPolicy.DESTROY if self.environment == "development" else RemovalPolicy.RETAIN
        )
        
        # Enable API Gateway access logging
        self.api_gateway.deployment_stage.add_property_override(
            "AccessLogSetting",
            {
                "DestinationArn": api_log_group.log_group_arn,
                "Format": json.dumps({
                    "requestId": "$context.requestId",
                    "requestTime": "$context.requestTime",
                    "httpMethod": "$context.httpMethod",
                    "resourcePath": "$context.resourcePath",
                    "status": "$context.status",
                    "protocol": "$context.protocol",
                    "responseLength": "$context.responseLength",
                    "requestLength": "$context.requestLength",
                    "responseTime": "$context.responseTime",
                    "sourceIp": "$context.identity.sourceIp",
                    "userAgent": "$context.identity.userAgent",
                    "user": "$context.identity.user",
                    "cognitoIdentityId": "$context.identity.cognitoIdentityId",
                    "cognitoAuthenticationType": "$context.identity.cognitoAuthenticationType",
                    "error.message": "$context.error.message",
                    "error.messageString": "$context.error.messageString",
                    "integration.error": "$context.integration.error",
                    "integration.status": "$context.integration.status",
                    "integration.latency": "$context.integration.latency",
                    "integration.requestId": "$context.integration.requestId"
                })
            }
        )
        
        # Create CloudWatch metrics and alarms for security monitoring
        self._create_security_alarms()
        
        # Create custom metrics for API security events
        self._create_custom_security_metrics()
    
    def _create_security_alarms(self):
        """Create CloudWatch alarms for API security monitoring"""
        
        # Import CloudWatch modules
        from aws_cdk import (
            aws_cloudwatch as cloudwatch,
            aws_sns as sns,
            aws_cloudwatch_actions as cloudwatch_actions
        )
        
        # High error rate alarm (4xx errors)
        client_error_alarm = cloudwatch.Alarm(
            self,
            "APIClientErrorAlarm",
            alarm_name=f"tutor-system-api-client-errors-{self.environment}",
            alarm_description="High rate of 4xx client errors in API Gateway",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="4XXError",
                dimensions_map={
                    "ApiName": self.api_gateway.rest_api_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=50 if self.environment == "production" else 20,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Server error alarm (5xx errors)
        server_error_alarm = cloudwatch.Alarm(
            self,
            "APIServerErrorAlarm",
            alarm_name=f"tutor-system-api-server-errors-{self.environment}",
            alarm_description="High rate of 5xx server errors in API Gateway",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                dimensions_map={
                    "ApiName": self.api_gateway.rest_api_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=10 if self.environment == "production" else 5,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # High latency alarm
        latency_alarm = cloudwatch.Alarm(
            self,
            "APILatencyAlarm",
            alarm_name=f"tutor-system-api-latency-{self.environment}",
            alarm_description="High API Gateway latency",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Latency",
                dimensions_map={
                    "ApiName": self.api_gateway.rest_api_name
                },
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=5000,  # 5 seconds
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Throttling alarm
        throttle_alarm = cloudwatch.Alarm(
            self,
            "APIThrottleAlarm",
            alarm_name=f"tutor-system-api-throttling-{self.environment}",
            alarm_description="API Gateway throttling detected",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="ThrottledRequests",
                dimensions_map={
                    "ApiName": self.api_gateway.rest_api_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=10,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Create SNS topic for security alerts (if in production)
        if self.environment == "production":
            security_alerts_topic = sns.Topic(
                self,
                "SecurityAlertsTopic",
                topic_name=f"tutor-system-security-alerts-{self.environment}",
                display_name="Tutor System Security Alerts"
            )
            
            # Add alarms to SNS topic
            for alarm in [client_error_alarm, server_error_alarm, latency_alarm, throttle_alarm]:
                alarm.add_alarm_action(cloudwatch_actions.SnsAction(security_alerts_topic))
    
    def _create_custom_security_metrics(self):
        """Create custom CloudWatch metrics for security events"""
        
        # Import required modules
        from aws_cdk import (
            aws_logs as logs,
            aws_logs_destinations as logs_destinations
        )
        
        # Create Lambda function for custom security metrics
        security_metrics_function = _lambda.Function(
            self,
            "SecurityMetricsFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=_lambda.Code.from_inline("""
import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudwatch = boto3.client('cloudwatch')

def lambda_handler(event, context):
    try:
        # Parse CloudWatch Logs event
        if 'awslogs' in event:
            import gzip
            import base64
            
            # Decode and decompress log data
            compressed_payload = base64.b64decode(event['awslogs']['data'])
            uncompressed_payload = gzip.decompress(compressed_payload)
            log_data = json.loads(uncompressed_payload)
            
            # Process log events for security metrics
            for log_event in log_data['logEvents']:
                try:
                    message = json.loads(log_event['message'])
                    
                    # Track authentication failures
                    if message.get('status') == '401':
                        put_custom_metric('AuthenticationFailures', 1)
                    
                    # Track authorization failures
                    elif message.get('status') == '403':
                        put_custom_metric('AuthorizationFailures', 1)
                    
                    # Track rate limiting
                    elif message.get('status') == '429':
                        put_custom_metric('RateLimitExceeded', 1)
                    
                    # Track large request attempts
                    elif int(message.get('requestLength', 0)) > 10485760:  # 10MB
                        put_custom_metric('LargeRequestAttempts', 1)
                        
                except json.JSONDecodeError:
                    # Skip non-JSON log messages
                    continue
        
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Error processing security metrics: {str(e)}")
        return {'statusCode': 500}

def put_custom_metric(metric_name, value):
    try:
        cloudwatch.put_metric_data(
            Namespace='TutorSystem/Security',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    except Exception as e:
        logger.error(f"Failed to put metric {metric_name}: {str(e)}")
            """),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "ENVIRONMENT": self.environment
            }
        )
        
        # Grant CloudWatch permissions to the security metrics function
        security_metrics_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudwatch:PutMetricData"
                ],
                resources=["*"]
            )
        )