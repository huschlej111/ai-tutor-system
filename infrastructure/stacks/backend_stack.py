"""
Backend Stack for Know-It-All Tutor System
Contains Lambda functions and API Gateway
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecr_assets as ecr_assets,
    Duration,
    CfnOutput
)
from constructs import Construct


class BackendStack(Stack):
    """
    Backend infrastructure stack containing Lambda functions and API Gateway.
    This stack changes frequently.
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        network_stack,
        database_stack,
        auth_stack,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Import resources from other stacks
        self.vpc = network_stack.vpc
        self.lambda_security_group = network_stack.lambda_security_group
        self.database = database_stack.database
        self.db_credentials = database_stack.db_credentials
        self.user_pool = auth_stack.user_pool
        self.user_pool_client = auth_stack.user_pool_client
        
        # Create Lambda Layer for shared utilities
        self.shared_layer = _lambda.LayerVersion(
            self,
            "SharedUtilitiesLayer",
            code=_lambda.Code.from_asset(
                "infrastructure/lambda_layer",
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
            description="Shared utilities for authentication and security"
        )
        
        # Create DB Proxy Lambda (inside VPC)
        self.db_proxy_lambda = _lambda.Function(
            self,
            "DBProxyFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda_functions/db_proxy"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
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
        self.db_credentials.grant_read(self.db_proxy_lambda)
        
        # Create Auth Lambda (outside VPC)
        self.auth_lambda = _lambda.Function(
            self,
            "AuthFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda_functions/auth"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "STAGE": "prod",
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name
            },
            description="Auth Lambda - handles Cognito, invokes DB proxy"
        )
        self.user_pool.grant(self.auth_lambda, "cognito-idp:AdminConfirmSignUp", "cognito-idp:AdminGetUser")
        self.db_proxy_lambda.grant_invoke(self.auth_lambda)
        
        # Create User Profile Lambda
        self.profile_lambda = _lambda.Function(
            self,
            "ProfileFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda_functions/user_profile"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
            },
            description="User profile management"
        )
        self.db_proxy_lambda.grant_invoke(self.profile_lambda)
        
        # Create Domain Management Lambda
        self.domain_lambda = _lambda.Function(
            self,
            "DomainFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda_functions/domain_management"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
            },
            description="Domain management operations"
        )
        self.db_proxy_lambda.grant_invoke(self.domain_lambda)
        
        # Create Progress Tracking Lambda
        self.progress_lambda = _lambda.Function(
            self,
            "ProgressFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda_functions/progress_tracking"),
            timeout=Duration.seconds(30),
            memory_size=256,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
            },
            description="Progress tracking operations"
        )
        self.db_proxy_lambda.grant_invoke(self.progress_lambda)
        
        # Create Quiz Engine Lambda
        self.quiz_engine_lambda = _lambda.Function(
            self,
            "QuizEngineFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambda_functions/quiz_engine"),
            timeout=Duration.seconds(30),
            memory_size=512,
            layers=[self.shared_layer],
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
            },
            description="Quiz engine - manages quiz sessions"
        )
        self.db_proxy_lambda.grant_invoke(self.quiz_engine_lambda)
        
        # Create Answer Evaluator Lambda (container-based with ML model)
        self.answer_evaluator_lambda = _lambda.DockerImageFunction(
            self,
            "AnswerEvaluatorFunction",
            code=_lambda.DockerImageCode.from_image_asset(
                ".",  # Build from current directory (project root)
                file="lambda/answer-evaluator/Dockerfile",
                exclude=[
                    "infrastructure/cdk.out",
                    "frontend/node_modules",
                    "frontend/dist",
                    ".git",
                    "venv",
                    "__pycache__",
                    "*.pyc"
                ]
            ),
            timeout=Duration.seconds(60),
            memory_size=2048,
            environment={
                "DB_PROXY_FUNCTION_NAME": self.db_proxy_lambda.function_name,
            },
            description="Answer evaluator with ML model"
        )
        self.db_proxy_lambda.grant_invoke(self.answer_evaluator_lambda)
        
        # Create API Gateway
        self.api = apigateway.RestApi(
            self,
            "TutorAPI",
            rest_api_name="know-it-all-tutor-api-multistack-dev",
            description="API for Know-It-All Tutor System",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],  # Will be restricted in production
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200
            )
        )
        
        # Create Cognito Authorizer
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[self.user_pool]
        )
        
        # Add API routes
        # Auth routes (no authorization)
        auth_resource = self.api.root.add_resource("auth")
        auth_resource.add_resource("register").add_method(
            "POST",
            apigateway.LambdaIntegration(self.auth_lambda)
        )
        auth_resource.add_resource("login").add_method(
            "POST",
            apigateway.LambdaIntegration(self.auth_lambda)
        )
        
        # Profile routes (with authorization)
        profile_resource = self.api.root.add_resource("profile")
        profile_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.profile_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Domain routes (with authorization)
        domains_resource = self.api.root.add_resource("domains")
        domains_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.domain_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Quiz routes (with authorization)
        quiz_resource = self.api.root.add_resource("quiz")
        quiz_resource.add_resource("start").add_method(
            "POST",
            apigateway.LambdaIntegration(self.quiz_engine_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        quiz_resource.add_resource("evaluate").add_method(
            "POST",
            apigateway.LambdaIntegration(self.answer_evaluator_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # Progress routes (with authorization)
        progress_resource = self.api.root.add_resource("progress")
        progress_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.progress_lambda),
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )
        
        # CloudFormation Outputs
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name=f"{construct_id}-ApiUrl"
        )
        
        CfnOutput(
            self,
            "QuizEngineFunctionName",
            value=self.quiz_engine_lambda.function_name,
            description="Quiz Engine Lambda function name"
        )
        
        CfnOutput(
            self,
            "AnswerEvaluatorFunctionName",
            value=self.answer_evaluator_lambda.function_name,
            description="Answer Evaluator Lambda function name"
        )
