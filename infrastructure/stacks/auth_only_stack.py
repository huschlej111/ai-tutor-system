import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    Duration,
    RemovalPolicy
)
from constructs import Construct

class TutorSystemStack(Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Step 1: Create VPC (Free Tier Optimized - Single AZ for instances)
        self.vpc = ec2.Vpc(
            self,
            "TutorVPC",
            max_azs=2,  # Need 2 AZs for RDS subnet group requirement (subnets are free)
            nat_gateways=0,  # No NAT Gateway ($32/month cost)
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,  # No NAT needed
                    cidr_mask=24
                )
            ]
        )
        
        # Step 1.5: Create Security Groups
        # RDS Security Group - allows PostgreSQL access from Lambda
        self.rds_security_group = ec2.SecurityGroup(
            self,
            "RDSSecurityGroup",
            vpc=self.vpc,
            description="Security group for RDS PostgreSQL",
            allow_all_outbound=False
        )
        
        # Lambda Security Group (for future use when Lambda moves to VPC)
        self.lambda_security_group = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True
        )
        
        # Allow Lambda to connect to RDS on PostgreSQL port
        self.rds_security_group.add_ingress_rule(
            peer=self.lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda to access RDS PostgreSQL"
        )
        
        # Step 1.6: Create VPC Endpoints (Free Tier - no NAT Gateway needed)
        # Secrets Manager endpoint - Lambda needs to read DB credentials
        self.secrets_endpoint = ec2.InterfaceVpcEndpoint(
            self,
            "SecretsManagerEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.lambda_security_group]
        )
        
        # Step 1.7: Create database credentials in Secrets Manager
        self.db_credentials = secretsmanager.Secret(
            self,
            "DBCredentials",
            secret_name="tutor-system/db-credentials-dev",
            description="RDS PostgreSQL credentials for tutor system",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username":"tutor_admin"}',
                generate_string_key="password",
                exclude_characters="\"@/\\ '",
                password_length=32
            ),
            removal_policy=RemovalPolicy.DESTROY  # Dev only - delete with stack
        )
        
        # Step 1.8: Create RDS PostgreSQL (Free Tier - t4g.micro)
        self.database = rds.DatabaseInstance(
            self,
            "TutorDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_6  # Latest stable
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON,  # t4g
                ec2.InstanceSize.MICRO  # Free tier eligible
            ),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[self.rds_security_group],
            credentials=rds.Credentials.from_secret(self.db_credentials),
            database_name="tutor_system",
            allocated_storage=20,  # Free tier: 20GB
            max_allocated_storage=20,  # Disable autoscaling to stay in free tier
            storage_encrypted=True,  # Always encrypt
            backup_retention=Duration.days(7),  # Free tier: 7 days
            deletion_protection=False,  # Dev environment
            removal_policy=RemovalPolicy.DESTROY,  # Dev only
            publicly_accessible=False,  # Security best practice
            multi_az=False,  # Single AZ for free tier
        )
        
        # Step 2: Create Cognito User Pool
        self.user_pool = cognito.UserPool(
            self,
            "AuthUserPool",
            user_pool_name="know-it-all-tutor-dev",
            # Users sign in with email, not username
            sign_in_aliases=cognito.SignInAliases(email=True),
            # Password requirements
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            # NO EMAIL VERIFICATION for dev - users are immediately confirmed
            auto_verify=cognito.AutoVerifiedAttrs(),  # Empty = no verification
            # Allow users to sign up themselves (required for registration endpoint)
            self_sign_up_enabled=True,
            # Lambda triggers for auto-confirmation
            lambda_triggers=cognito.UserPoolTriggers(
                pre_sign_up=None  # Will be set after Lambda creation
            ),
            # Clean up when stack is deleted (dev environment)
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        
        # Step 3: Create User Pool Client (allows your app to connect)
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "AuthUserPoolClient",
            user_pool=self.user_pool,
            user_pool_client_name="know-it-all-tutor-web-client-dev",
            # Allow username/password authentication
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            # Token validity periods
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            # Don't generate a client secret (for web apps)
            generate_secret=False
        )
        
        # Step 3.5: Create Pre-SignUp Lambda Trigger (auto-confirm users)
        self.pre_signup_lambda = _lambda.Function(
            self,
            "PreSignUpTrigger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/cognito_pre_signup"),
            timeout=Duration.seconds(10),
            memory_size=128,
            description="Cognito Pre-SignUp trigger - auto-confirms users"
        )
        
        # Grant Cognito permission to invoke the Lambda
        self.pre_signup_lambda.add_permission(
            "CognitoInvoke",
            principal=iam.ServicePrincipal("cognito-idp.amazonaws.com"),
            source_arn=self.user_pool.user_pool_arn
        )
        
        # Add trigger to User Pool
        self.user_pool.add_trigger(
            cognito.UserPoolOperation.PRE_SIGN_UP,
            self.pre_signup_lambda
        )
        

        # Step 3.5: Create Lambda Layer for shared utilities
        # Uses Docker to build layer with Amazon Linux 2023 for Lambda compatibility
        self.shared_layer = _lambda.LayerVersion(
            self,
            "SharedUtilitiesLayer",
            code=_lambda.Code.from_asset(
                "lambda_layer",
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output/python && "
                        "cp -r python/* /asset-output/python/"
                    ]
                )
            ),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Shared utilities for authentication and security (Docker build)"
        )

        # Step 4: Create Lambda B (DB Proxy) - Inside VPC
        self.db_proxy_lambda = _lambda.Function(
            self,
            "DBProxyFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/db_proxy"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            # Inside VPC to access RDS
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[self.lambda_security_group],
            environment={
                "DB_SECRET_ARN": self.db_credentials.secret_arn,
                "DB_NAME": "tutor_system"
            },
            description="Database proxy Lambda - handles all DB operations from VPC"
        )
        
        # Grant DB proxy access to Secrets Manager
        self.db_credentials.grant_read(self.db_proxy_lambda)
        
        # Step 5: Create Lambda A (Auth) - Outside VPC
        self.auth_lambda = _lambda.Function(
            self,
            "AuthFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/auth"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            # Outside VPC to access Cognito (public service)
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "STAGE": "prod",
                # DB Proxy Lambda function name
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name
            },
            description="Auth Lambda - handles Cognito, invokes DB proxy for database operations"
        )
        
        # Grant Lambda permission to confirm users (for dev auto-confirmation)
        self.user_pool.grant(
            self.auth_lambda,
            "cognito-idp:AdminConfirmSignUp",
            "cognito-idp:AdminGetUser"
        )
        
        # Grant Auth Lambda permission to invoke DB Proxy Lambda
        self.db_proxy_lambda.grant_invoke(self.auth_lambda)
        
        # Step 5.5: Create User Profile Lambda (Lambda A pattern)
        self.profile_lambda = _lambda.Function(
            self,
            "ProfileFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/user_profile"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            # Outside VPC to access Cognito (public service)
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
            }
        )
        
        # Grant Profile Lambda permission to invoke DB Proxy Lambda
        self.db_proxy_lambda.grant_invoke(self.profile_lambda)
        
        # Step 5.7: Create Domain Management Lambda (Lambda A pattern)
        self.domain_lambda = _lambda.Function(
            self,
            "DomainFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/domain_management"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            # Outside VPC to access Cognito (public service)
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
            }
        )
        
        # Grant Domain Lambda permission to invoke DB Proxy Lambda
        self.db_proxy_lambda.grant_invoke(self.domain_lambda)
        
        # Step 5: Create Progress Tracking Lambda (Lambda A - outside VPC)
        self.progress_lambda = _lambda.Function(
            self,
            "ProgressFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/progress_tracking"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            # Outside VPC to access Cognito (public service)
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
            }
        )
        
        # Grant Progress Lambda permission to invoke DB Proxy Lambda
        self.db_proxy_lambda.grant_invoke(self.progress_lambda)
        
        # Step 5.9: Create ML Inference Lambda (Container-based with ML model)
        # Pure ML inference - rarely changes
        inference_repo = ecr.Repository.from_repository_name(
            self,
            "InferenceRepo",
            repository_name="answer-evaluator-inference"
        )
        
        self.inference_lambda = _lambda.DockerImageFunction(
            self,
            "InferenceFunction",
            code=_lambda.DockerImageCode.from_ecr(
                repository=inference_repo,
                tag_or_digest="latest"
            ),
            timeout=Duration.seconds(120),
            memory_size=2048,
            environment={
                "MODEL_PATH": "/opt/ml/model"
            },
            description="ML Inference Lambda - Semantic similarity calculation only"
        )
        
        # Step 5.10: Create Answer Evaluator Lambda (Zip-based business logic)
        # Fast deployment for threshold/feedback changes
        self.answer_evaluator_lambda = _lambda.Function(
            self,
            "AnswerEvaluatorFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/answer_evaluator"),
            timeout=Duration.seconds(120),  # Increased to handle inference Lambda cold starts
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "INFERENCE_FUNCTION_NAME": self.inference_lambda.function_name,
                "THRESHOLD_EXCELLENT": "0.85",
                "THRESHOLD_GOOD": "0.70",
                "THRESHOLD_PARTIAL": "0.50",
                "LOG_LEVEL": "INFO",
                "REGION": self.region
            },
            description="Answer Evaluator - Business logic and API routing"
        )
        
        # Grant Answer Evaluator permission to invoke Inference Lambda
        self.inference_lambda.grant_invoke(self.answer_evaluator_lambda)
        
        # Step 5.11: Create Quiz Engine Lambda (Lambda A pattern)
        self.quiz_engine_lambda = _lambda.Function(
            self,
            "QuizEngineFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src/lambda_functions/quiz_engine"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            # Outside VPC to access Cognito (public service)
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
                "ANSWER_EVALUATOR_FUNCTION_NAME": self.answer_evaluator_lambda.function_name,
                "LOG_LEVEL": "INFO",
                "REGION": self.region
            },
            description="Quiz Engine Lambda - manages quiz sessions and question flow"
        )
        
        # Grant Quiz Engine permission to invoke DB Proxy Lambda
        self.db_proxy_lambda.grant_invoke(self.quiz_engine_lambda)
        
        # Grant Quiz Engine permission to invoke Answer Evaluator Lambda
        self.answer_evaluator_lambda.grant_invoke(self.quiz_engine_lambda)
        
        # Lambda Bridge Architecture:
        # ✅ Lambda A (Auth) - Outside VPC, can reach Cognito
        # ✅ Lambda A (Profile) - Outside VPC, can reach Cognito
        # ✅ Lambda A (Domain) - Outside VPC, can reach Cognito
        # ✅ Lambda A (Progress) - Outside VPC, can reach Cognito
        # ✅ Lambda A (Quiz Engine) - Outside VPC, can reach Cognito
        # ✅ Lambda A (Answer Evaluator) - Outside VPC, ML model
        # ✅ Lambda B (DB Proxy) - Inside VPC, can reach RDS
        # ✅ Lambda A invokes Lambda B via AWS internal network (no NAT needed)
        # ✅ Completely free tier eligible
        
        # Step 6: Create API Gateway
        self.api = apigateway.RestApi(
            self,
            "AuthAPI",
            rest_api_name="tutor-auth-api-dev",
            description="Authentication API for Know-It-All Tutor - Dev",
            # Enable CORS for frontend to call this API
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["http://localhost:3000"],  # ✅ Only allow your frontend
                allow_methods=["GET", "POST", "PUT", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization"]
            )
        )
        
        # Add CORS headers to Gateway error responses (401, 403, 500, etc.)
        # This ensures CORS headers are present even when authorizer rejects requests
        cors_headers = {
            'Access-Control-Allow-Origin': "'https://d1o8fugfe04j49.cloudfront.net'",
            'Access-Control-Allow-Headers': "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
            'Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
            'Access-Control-Allow-Credentials': "'true'"
        }
        
        # Add CORS to common error responses
        for response_type in [
            apigateway.ResponseType.UNAUTHORIZED,
            apigateway.ResponseType.ACCESS_DENIED,
            apigateway.ResponseType.DEFAULT_4_XX,
            apigateway.ResponseType.DEFAULT_5_XX
        ]:
            self.api.add_gateway_response(
                f"CorsGatewayResponse{response_type.response_type}",
                type=response_type,
                response_headers=cors_headers
            )
        
        # Create Cognito Authorizer for protected routes
        self.cognito_authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[self.user_pool]
        )

        # Step 7: Create API routes and connect to Lambda
        # Create /auth resource (public routes)
        auth_resource = self.api.root.add_resource("auth")
        
        # Create Lambda integration
        auth_integration = apigateway.LambdaIntegration(self.auth_lambda)
        
        # Add routes: POST /auth/register
        register_resource = auth_resource.add_resource("register")
        register_resource.add_method("POST", auth_integration)
        
        # Add routes: POST /auth/login
        login_resource = auth_resource.add_resource("login")
        login_resource.add_method("POST", auth_integration)
        
        # Add routes: GET /auth/validate
        validate_resource = auth_resource.add_resource("validate")
        validate_resource.add_method("GET", auth_integration)
        
        # Define CORS configuration for all protected resources
        cors_options = apigateway.CorsOptions(
            allow_origins=["https://d1o8fugfe04j49.cloudfront.net"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Authorization",
                "X-Amz-Date",
                "X-Api-Key",
                "X-Amz-Security-Token"
            ],
            allow_credentials=True
        )
        
        # Create /profile resource (protected routes)
        profile_resource = self.api.root.add_resource(
            "profile",
            default_cors_preflight_options=cors_options
        )
        profile_integration = apigateway.LambdaIntegration(self.profile_lambda)
        
        # Add routes: GET /profile (requires authentication)
        profile_resource.add_method(
            "GET", 
            profile_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Add routes: PUT /profile (requires authentication)
        profile_resource.add_method(
            "PUT", 
            profile_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Create /domains resource (protected routes)
        domains_resource = self.api.root.add_resource(
            "domains",
            default_cors_preflight_options=cors_options
        )
        domain_integration = apigateway.LambdaIntegration(self.domain_lambda)
        
        # POST /domains (create domain)
        domains_resource.add_method(
            "POST",
            domain_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # GET /domains (list domains)
        domains_resource.add_method(
            "GET",
            domain_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # /domains/{id}
        domain_id_resource = domains_resource.add_resource(
            "{id}",
            default_cors_preflight_options=cors_options
        )
        
        domain_id_resource.add_method(
            "GET",
            domain_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        domain_id_resource.add_method(
            "PUT",
            domain_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        domain_id_resource.add_method(
            "DELETE",
            domain_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # /domains/{id}/terms
        terms_resource = domain_id_resource.add_resource(
            "terms",
            default_cors_preflight_options=cors_options
        )
        
        terms_resource.add_method(
            "POST",
            domain_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        terms_resource.add_method(
            "GET",
            domain_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Step 8: Progress Tracking Routes
        progress_integration = apigateway.LambdaIntegration(self.progress_lambda)
        
        # /progress
        progress_resource = self.api.root.add_resource(
            "progress",
            default_cors_preflight_options=cors_options
        )
        
        # /progress/dashboard
        dashboard_resource = progress_resource.add_resource(
            "dashboard",
            default_cors_preflight_options=cors_options
        )
        
        dashboard_resource.add_method(
            "GET",
            progress_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Step 8.5: Quiz Engine and Answer Evaluation Routes
        quiz_integration = apigateway.LambdaIntegration(self.quiz_engine_lambda)
        answer_evaluator_integration = apigateway.LambdaIntegration(self.answer_evaluator_lambda)
        
        # /quiz
        quiz_resource = self.api.root.add_resource(
            "quiz",
            default_cors_preflight_options=cors_options
        )
        
        # POST /quiz/start - Start a new quiz session
        start_resource = quiz_resource.add_resource(
            "start",
            default_cors_preflight_options=cors_options
        )
        start_resource.add_method(
            "POST",
            quiz_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # GET /quiz/question - Get next question in current session
        question_resource = quiz_resource.add_resource(
            "question",
            default_cors_preflight_options=cors_options
        )
        question_resource.add_method(
            "GET",
            quiz_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # POST /quiz/answer - Submit answer for current question
        answer_resource = quiz_resource.add_resource(
            "answer",
            default_cors_preflight_options=cors_options
        )
        answer_resource.add_method(
            "POST",
            quiz_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # POST /quiz/pause - Pause current quiz session
        pause_resource = quiz_resource.add_resource(
            "pause",
            default_cors_preflight_options=cors_options
        )
        pause_resource.add_method(
            "POST",
            quiz_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # POST /quiz/resume - Resume paused quiz session
        resume_resource = quiz_resource.add_resource(
            "resume",
            default_cors_preflight_options=cors_options
        )
        resume_resource.add_method(
            "POST",
            quiz_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # /quiz/session
        session_resource = quiz_resource.add_resource(
            "session",
            default_cors_preflight_options=cors_options
        )
        
        # /quiz/session/{sessionId}
        session_id_resource = session_resource.add_resource(
            "{sessionId}",
            default_cors_preflight_options=cors_options
        )
        
        # GET /quiz/session/{sessionId} - Get session details
        session_id_resource.add_method(
            "GET",
            quiz_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # DELETE /quiz/session/{sessionId} - Delete session
        session_id_resource.add_method(
            "DELETE",
            quiz_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # /quiz/evaluate - Answer evaluation endpoints
        evaluate_resource = quiz_resource.add_resource(
            "evaluate",
            default_cors_preflight_options=cors_options
        )
        
        # POST /quiz/evaluate - Evaluate single answer
        evaluate_resource.add_method(
            "POST",
            answer_evaluator_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # /quiz/evaluate/batch
        batch_resource = evaluate_resource.add_resource(
            "batch",
            default_cors_preflight_options=cors_options
        )
        
        # POST /quiz/evaluate/batch - Evaluate multiple answers
        batch_resource.add_method(
            "POST",
            answer_evaluator_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # /quiz/evaluate/health
        health_resource = evaluate_resource.add_resource(
            "health",
            default_cors_preflight_options=cors_options
        )
        
        # GET /quiz/evaluate/health - Health check (no auth required)
        health_resource.add_method(
            "GET",
            answer_evaluator_integration
        )
        
        # Step 9: Frontend Hosting (S3 + CloudFront)
        # Create S3 bucket for static website hosting
        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            website_index_document="index.html",
            website_error_document="index.html",  # SPA routing
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False
            ),
            removal_policy=RemovalPolicy.DESTROY,  # For dev environment
            auto_delete_objects=True  # Clean up on stack deletion
        )
        
        # Create CloudFront distribution
        self.distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3StaticWebsiteOrigin(self.frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # Use only North America and Europe
            comment="Know-It-All Tutor Frontend - Dev"
        )
        
        # Deploy frontend build to S3
        self.frontend_deployment = s3deploy.BucketDeployment(
            self,
            "DeployFrontend",
            sources=[s3deploy.Source.asset("../frontend/dist")],
            destination_bucket=self.frontend_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],  # Invalidate CloudFront cache on deployment
        )

        # Step 10: Output important values
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
            "ApiUrl",
            value=self.api.url,
            description="API Gateway URL"
        )
        
        cdk.CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID"
        )
        
        cdk.CfnOutput(
            self,
            "DatabaseEndpoint",
            value=self.database.db_instance_endpoint_address,
            description="RDS PostgreSQL endpoint"
        )
        
        cdk.CfnOutput(
            self,
            "DatabaseSecretArn",
            value=self.db_credentials.secret_arn,
            description="ARN of database credentials in Secrets Manager"
        )
        
        cdk.CfnOutput(
            self,
            "DBProxyFunctionName",
            value=self.db_proxy_lambda.function_name,
            description="DB Proxy Lambda function name"
        )
        
        cdk.CfnOutput(
            self,
            "FrontendUrl",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="CloudFront URL for frontend application"
        )
        
        cdk.CfnOutput(
            self,
            "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="S3 bucket name for frontend"
        )
        
        cdk.CfnOutput(
            self,
            "InferenceFunctionName",
            value=self.inference_lambda.function_name,
            description="ML Inference Lambda function name"
        )
        
        cdk.CfnOutput(
            self,
            "InferenceFunctionArn",
            value=self.inference_lambda.function_arn,
            description="ML Inference Lambda function ARN"
        )
        
        cdk.CfnOutput(
            self,
            "AnswerEvaluatorFunctionName",
            value=self.answer_evaluator_lambda.function_name,
            description="Answer Evaluator Lambda function name"
        )
        
        cdk.CfnOutput(
            self,
            "AnswerEvaluatorFunctionArn",
            value=self.answer_evaluator_lambda.function_arn,
            description="Answer Evaluator Lambda function ARN"
        )
        
        cdk.CfnOutput(
            self,
            "QuizEngineFunctionName",
            value=self.quiz_engine_lambda.function_name,
            description="Quiz Engine Lambda function name"
        )
        
        cdk.CfnOutput(
            self,
            "QuizEngineFunctionArn",
            value=self.quiz_engine_lambda.function_arn,
            description="Quiz Engine Lambda function ARN"
        )
