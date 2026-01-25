"""
AWS CodePipeline Stack for Know-It-All Tutor System
Implements automated CI/CD pipeline with GitHub integration
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_s3 as s3,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import Dict, Any


class PipelineStack(Stack):
    """CI/CD Pipeline stack for automated deployment"""
    
    def __init__(self, scope: Construct, construct_id: str, environment: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment = environment
        
        # Create S3 bucket for pipeline artifacts
        self.artifacts_bucket = self._create_artifacts_bucket()
        
        # Create CodeBuild projects
        self.build_project = self._create_build_project()
        self.deploy_project = self._create_deploy_project()
        
        # Create CodePipeline
        self.pipeline = self._create_pipeline()
        
        # Create monitoring and alerting
        self._create_pipeline_monitoring()
        
        # Create outputs
        self._create_outputs()
    
    def _create_artifacts_bucket(self) -> s3.Bucket:
        """Create S3 bucket for pipeline artifacts"""
        return s3.Bucket(
            self,
            "PipelineArtifactsBucket",
            bucket_name=f"tutor-system-pipeline-artifacts-{self.environment}-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY if self.environment == "development" else RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldArtifacts",
                    enabled=True,
                    expiration=Duration.days(30),
                    noncurrent_version_expiration=Duration.days(7)
                )
            ]
        )
    
    def _create_build_project(self) -> codebuild.Project:
        """Create CodeBuild project for testing and packaging"""
        
        # Create service role for CodeBuild
        build_role = iam.Role(
            self,
            "CodeBuildServiceRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            inline_policies={
                "CodeBuildPolicy": iam.PolicyDocument(
                    statements=[
                        # CloudWatch Logs permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/*"
                            ]
                        ),
                        # S3 permissions for artifacts
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:GetObjectVersion",
                                "s3:PutObject"
                            ],
                            resources=[
                                f"{self.artifacts_bucket.bucket_arn}/*"
                            ]
                        ),
                        # CodeBuild report permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "codebuild:CreateReportGroup",
                                "codebuild:CreateReport",
                                "codebuild:UpdateReport",
                                "codebuild:BatchPutTestCases"
                            ],
                            resources=[
                                f"arn:aws:codebuild:{self.region}:{self.account}:report-group/*"
                            ]
                        ),
                        # Secrets Manager permissions for database tests
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "secretsmanager:GetSecretValue"
                            ],
                            resources=[
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*"
                            ]
                        )
                    ]
                )
            }
        )
        
        return codebuild.Project(
            self,
            "TutorSystemBuildProject",
            project_name=f"tutor-system-build-{self.environment}",
            description=f"Build and test project for Know-It-All Tutor System - {self.environment}",
            role=build_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.MEDIUM,
                privileged=False,
                environment_variables={
                    "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                        value=self.environment
                    ),
                    "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(
                        value=self.region
                    ),
                    "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(
                        value=self.account
                    ),
                    "ARTIFACTS_BUCKET": codebuild.BuildEnvironmentVariable(
                        value=self.artifacts_bucket.bucket_name
                    )
                }
            ),
            source=codebuild.Source.git_hub(
                owner="your-github-username",  # Replace with actual GitHub username
                repo="know-it-all-tutor",      # Replace with actual repo name
                webhook=True,
                webhook_filters=[
                    codebuild.FilterGroup.in_event_of(
                        codebuild.EventAction.PUSH,
                        codebuild.EventAction.PULL_REQUEST_CREATED,
                        codebuild.EventAction.PULL_REQUEST_UPDATED
                    ).and_branch_is("main").or_branch_is("develop")
                ]
            ),
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yml"),
            artifacts=codebuild.Artifacts.s3(
                bucket=self.artifacts_bucket,
                include_build_id=True,
                package_zip=True
            ),
            timeout=Duration.minutes(60),
            cache=codebuild.Cache.local(
                codebuild.LocalCacheMode.DOCKER_LAYER,
                codebuild.LocalCacheMode.CUSTOM
            )
        )
    
    def _create_deploy_project(self) -> codebuild.Project:
        """Create CodeBuild project for deployment"""
        
        # Create service role for deployment
        deploy_role = iam.Role(
            self,
            "CodeDeployServiceRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("PowerUserAccess")
            ],
            inline_policies={
                "DeploymentPolicy": iam.PolicyDocument(
                    statements=[
                        # CloudFormation permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cloudformation:*"
                            ],
                            resources=["*"]
                        ),
                        # IAM permissions for CDK deployment
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "iam:*"
                            ],
                            resources=["*"]
                        ),
                        # Lambda permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "lambda:*"
                            ],
                            resources=["*"]
                        ),
                        # API Gateway permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "apigateway:*"
                            ],
                            resources=["*"]
                        ),
                        # RDS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "rds:*"
                            ],
                            resources=["*"]
                        ),
                        # Cognito permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "cognito-idp:*"
                            ],
                            resources=["*"]
                        ),
                        # S3 permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:*"
                            ],
                            resources=["*"]
                        )
                    ]
                )
            }
        )
        
        # Create deployment buildspec
        deploy_buildspec = codebuild.BuildSpec.from_object({
            "version": "0.2",
            "phases": {
                "install": {
                    "runtime-versions": {
                        "python": "3.11",
                        "nodejs": "18"
                    },
                    "commands": [
                        "echo 'Installing deployment dependencies...'",
                        "python -m pip install --upgrade pip",
                        "pip install aws-cdk-lib constructs",
                        "npm install -g aws-cdk"
                    ]
                },
                "pre_build": {
                    "commands": [
                        "echo 'Preparing for deployment...'",
                        "cd infrastructure",
                        "python -m pip install -r requirements.txt"
                    ]
                },
                "build": {
                    "commands": [
                        "echo 'Deploying infrastructure...'",
                        "cdk bootstrap --context environment=$ENVIRONMENT",
                        "cdk deploy --all --require-approval never --context environment=$ENVIRONMENT --context account=$AWS_ACCOUNT_ID --context region=$AWS_DEFAULT_REGION",
                        "echo 'Running database migrations...'",
                        "aws lambda invoke --function-name tutor-db-migrate-$ENVIRONMENT --payload '{}' /tmp/migration-result.json",
                        "cat /tmp/migration-result.json"
                    ]
                },
                "post_build": {
                    "commands": [
                        "echo 'Deployment completed successfully'",
                        "echo 'Running post-deployment validation...'",
                        "aws apigateway test-invoke-method --rest-api-id $(aws apigateway get-rest-apis --query 'items[?name==`tutor-system-api-$ENVIRONMENT`].id' --output text) --resource-id $(aws apigateway get-resources --rest-api-id $(aws apigateway get-rest-apis --query 'items[?name==`tutor-system-api-$ENVIRONMENT`].id' --output text) --query 'items[?pathPart==`health`].id' --output text) --http-method GET || true"
                    ]
                }
            }
        })
        
        return codebuild.Project(
            self,
            "TutorSystemDeployProject",
            project_name=f"tutor-system-deploy-{self.environment}",
            description=f"Deployment project for Know-It-All Tutor System - {self.environment}",
            role=deploy_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                compute_type=codebuild.ComputeType.MEDIUM,
                privileged=True,  # Required for CDK deployment
                environment_variables={
                    "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                        value=self.environment
                    ),
                    "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(
                        value=self.region
                    ),
                    "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(
                        value=self.account
                    )
                }
            ),
            source=codebuild.Source.code_pipeline(),
            build_spec=deploy_buildspec,
            timeout=Duration.minutes(45)
        )
    
    def _create_pipeline(self) -> codepipeline.Pipeline:
        """Create the main CI/CD pipeline"""
        
        # Create source output artifact
        source_output = codepipeline.Artifact("SourceOutput")
        build_output = codepipeline.Artifact("BuildOutput")
        
        # Create GitHub source action
        source_action = codepipeline_actions.GitHubSourceAction(
            action_name="GitHub_Source",
            owner="your-github-username",  # Replace with actual GitHub username
            repo="know-it-all-tutor",      # Replace with actual repo name
            branch="main" if self.environment == "production" else "develop",
            oauth_token=cdk.SecretValue.secrets_manager("github-token"),  # Store GitHub token in Secrets Manager
            output=source_output,
            trigger=codepipeline_actions.GitHubTrigger.WEBHOOK
        )
        
        # Create build action
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="Build_and_Test",
            project=self.build_project,
            input=source_output,
            outputs=[build_output],
            environment_variables={
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.environment
                )
            }
        )
        
        # Create deployment action
        deploy_action = codepipeline_actions.CodeBuildAction(
            action_name="Deploy_Infrastructure",
            project=self.deploy_project,
            input=source_output,
            environment_variables={
                "ENVIRONMENT": codebuild.BuildEnvironmentVariable(
                    value=self.environment
                )
            }
        )
        
        # Create manual approval action for production
        approval_action = None
        if self.environment == "production":
            approval_action = codepipeline_actions.ManualApprovalAction(
                action_name="Manual_Approval",
                additional_information="Please review the build artifacts and approve deployment to production.",
                notification_topic=self._create_approval_topic()
            )
        
        # Build pipeline stages
        stages = [
            codepipeline.StageProps(
                stage_name="Source",
                actions=[source_action]
            ),
            codepipeline.StageProps(
                stage_name="Build",
                actions=[build_action]
            )
        ]
        
        # Add approval stage for production
        if approval_action:
            stages.append(
                codepipeline.StageProps(
                    stage_name="Approval",
                    actions=[approval_action]
                )
            )
        
        # Add deployment stage
        stages.append(
            codepipeline.StageProps(
                stage_name="Deploy",
                actions=[deploy_action]
            )
        )
        
        return codepipeline.Pipeline(
            self,
            "TutorSystemPipeline",
            pipeline_name=f"tutor-system-pipeline-{self.environment}",
            artifact_bucket=self.artifacts_bucket,
            stages=stages,
            restart_execution_on_update=True
        )
    
    def _create_approval_topic(self) -> sns.Topic:
        """Create SNS topic for manual approval notifications"""
        return sns.Topic(
            self,
            "ApprovalTopic",
            topic_name=f"tutor-system-approvals-{self.environment}",
            display_name="Tutor System Deployment Approvals"
        )
    
    def _create_pipeline_monitoring(self):
        """Create CloudWatch monitoring for the pipeline"""
        
        # Pipeline failure alarm
        pipeline_failure_alarm = cloudwatch.Alarm(
            self,
            "PipelineFailureAlarm",
            alarm_name=f"tutor-system-pipeline-failure-{self.environment}",
            alarm_description="Pipeline execution failed",
            metric=cloudwatch.Metric(
                namespace="AWS/CodePipeline",
                metric_name="PipelineExecutionFailure",
                dimensions_map={
                    "PipelineName": self.pipeline.pipeline_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Build failure alarm
        build_failure_alarm = cloudwatch.Alarm(
            self,
            "BuildFailureAlarm",
            alarm_name=f"tutor-system-build-failure-{self.environment}",
            alarm_description="Build project execution failed",
            metric=cloudwatch.Metric(
                namespace="AWS/CodeBuild",
                metric_name="FailedBuilds",
                dimensions_map={
                    "ProjectName": self.build_project.project_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Create SNS topic for pipeline alerts
        if self.environment == "production":
            alerts_topic = sns.Topic(
                self,
                "PipelineAlertsTopic",
                topic_name=f"tutor-system-pipeline-alerts-{self.environment}",
                display_name="Tutor System Pipeline Alerts"
            )
            
            # Add alarms to SNS topic
            pipeline_failure_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alerts_topic))
            build_failure_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alerts_topic))
    
    def _create_outputs(self):
        """Create CloudFormation outputs"""
        cdk.CfnOutput(
            self,
            "PipelineName",
            value=self.pipeline.pipeline_name,
            description="CodePipeline name"
        )
        
        cdk.CfnOutput(
            self,
            "BuildProjectName",
            value=self.build_project.project_name,
            description="CodeBuild project name"
        )
        
        cdk.CfnOutput(
            self,
            "ArtifactsBucketName",
            value=self.artifacts_bucket.bucket_name,
            description="Pipeline artifacts S3 bucket"
        )