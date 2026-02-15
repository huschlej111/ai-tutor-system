"""
Monitoring and Alerting Stack for Know-It-All Tutor System
Implements comprehensive CloudWatch monitoring, alarms, and cost tracking
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_budgets as budgets,
    aws_logs as logs,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    RemovalPolicy
)
from constructs import Construct
from typing import Dict, List, Optional


class MonitoringStack(Stack):
    """Comprehensive monitoring and alerting infrastructure"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        environment: str,
        notification_email: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = environment  # Changed from self.env_name to avoid conflict
        self.notification_email = notification_email
        
        # Create SNS topics for different alert types
        self.alert_topics = self._create_alert_topics()
        
        # Create CloudWatch dashboards
        self.dashboard = self._create_dashboard()
        
        # Create application monitoring alarms
        self._create_application_alarms()
        
        # Create infrastructure monitoring alarms
        self._create_infrastructure_alarms()
        
        # Create cost monitoring and budgets
        self._create_cost_monitoring()
        
        # Create custom metrics and log monitoring
        self._create_custom_monitoring()
        
        # Create automated incident response
        self._create_incident_response()
        
        # Create outputs
        self._create_outputs()
    
    def _create_alert_topics(self) -> Dict[str, sns.Topic]:
        """Create SNS topics for different types of alerts"""
        topics = {}
        
        # Critical alerts (immediate attention required)
        topics["critical"] = sns.Topic(
            self,
            "CriticalAlertsTopic",
            topic_name=f"tutor-system-critical-alerts-{self.env_name}",
            display_name="Critical Alerts - Know-It-All Tutor System"
        )
        
        # Warning alerts (attention needed but not urgent)
        topics["warning"] = sns.Topic(
            self,
            "WarningAlertsTopic",
            topic_name=f"tutor-system-warning-alerts-{self.env_name}",
            display_name="Warning Alerts - Know-It-All Tutor System"
        )
        
        # Cost alerts (budget and spending notifications)
        topics["cost"] = sns.Topic(
            self,
            "CostAlertsTopic",
            topic_name=f"tutor-system-cost-alerts-{self.env_name}",
            display_name="Cost Alerts - Know-It-All Tutor System"
        )
        
        # Security alerts (security-related notifications)
        topics["security"] = sns.Topic(
            self,
            "SecurityAlertsTopic",
            topic_name=f"tutor-system-security-alerts-{self.env_name}",
            display_name="Security Alerts - Know-It-All Tutor System"
        )
        
        # Add email subscription if provided
        if self.notification_email:
            for topic_name, topic in topics.items():
                topic.add_subscription(
                    sns_subscriptions.EmailSubscription(self.notification_email)
                )
        
        return topics
    
    def _create_dashboard(self) -> cloudwatch.Dashboard:
        """Create CloudWatch dashboard for system monitoring"""
        dashboard = cloudwatch.Dashboard(
            self,
            "TutorSystemDashboard",
            dashboard_name=f"TutorSystem-{self.env_name}",
            period_override=cloudwatch.PeriodOverride.AUTO
        )
        
        # API Gateway metrics
        api_widgets = [
            cloudwatch.GraphWidget(
                title="API Gateway - Request Count",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Count",
                        dimensions_map={"ApiName": f"tutor-system-api-{self.env_name}"},
                        statistic="Sum",
                        period=Duration.minutes(5)
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="API Gateway - Latency",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Latency",
                        dimensions_map={"ApiName": f"tutor-system-api-{self.env_name}"},
                        statistic="Average",
                        period=Duration.minutes(5)
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="Latency",
                        dimensions_map={"ApiName": f"tutor-system-api-{self.env_name}"},
                        statistic="Maximum",
                        period=Duration.minutes(5)
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="API Gateway - Error Rates",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="4XXError",
                        dimensions_map={"ApiName": f"tutor-system-api-{self.env_name}"},
                        statistic="Sum",
                        period=Duration.minutes(5)
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/ApiGateway",
                        metric_name="5XXError",
                        dimensions_map={"ApiName": f"tutor-system-api-{self.env_name}"},
                        statistic="Sum",
                        period=Duration.minutes(5)
                    )
                ],
                width=12,
                height=6
            )
        ]
        
        # Lambda metrics
        lambda_functions = [
            "tutor-auth", "tutor-domain-management", "tutor-quiz-engine",
            "tutor-answer-evaluation", "tutor-progress-tracking", "tutor-batch-upload"
        ]
        
        lambda_widgets = []
        for func in lambda_functions:
            lambda_widgets.extend([
                cloudwatch.GraphWidget(
                    title=f"Lambda - {func} - Invocations & Errors",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Invocations",
                            dimensions_map={"FunctionName": f"{func}-{self.env_name}"},
                            statistic="Sum",
                            period=Duration.minutes(5)
                        )
                    ],
                    right=[
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Errors",
                            dimensions_map={"FunctionName": f"{func}-{self.env_name}"},
                            statistic="Sum",
                            period=Duration.minutes(5)
                        )
                    ],
                    width=8,
                    height=6
                ),
                cloudwatch.GraphWidget(
                    title=f"Lambda - {func} - Duration",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/Lambda",
                            metric_name="Duration",
                            dimensions_map={"FunctionName": f"{func}-{self.env_name}"},
                            statistic="Average",
                            period=Duration.minutes(5)
                        )
                    ],
                    width=4,
                    height=6
                )
            ])
        
        # RDS metrics
        rds_widgets = [
            cloudwatch.GraphWidget(
                title="Aurora Serverless - ACU Utilization",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="ServerlessDatabaseCapacity",
                        dimensions_map={"DBClusterIdentifier": f"aurora-cluster-{self.env_name}"},
                        statistic="Average",
                        period=Duration.minutes(5)
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="Aurora Serverless - Connections",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="DatabaseConnections",
                        dimensions_map={"DBClusterIdentifier": f"aurora-cluster-{self.env_name}"},
                        statistic="Average",
                        period=Duration.minutes(5)
                    )
                ],
                width=6,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="Aurora Serverless - Query Performance",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="ReadLatency",
                        dimensions_map={"DBClusterIdentifier": f"aurora-cluster-{self.env_name}"},
                        statistic="Average",
                        period=Duration.minutes(5)
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="WriteLatency",
                        dimensions_map={"DBClusterIdentifier": f"aurora-cluster-{self.env_name}"},
                        statistic="Average",
                        period=Duration.minutes(5)
                    )
                ],
                width=6,
                height=6
            )
        ]
        
        # CloudFront metrics (if production)
        cloudfront_widgets = []
        if self.env_name == "production":
            cloudfront_widgets = [
                cloudwatch.GraphWidget(
                    title="CloudFront - Requests",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/CloudFront",
                            metric_name="Requests",
                            statistic="Sum",
                            period=Duration.minutes(5)
                        )
                    ],
                    width=6,
                    height=6
                ),
                cloudwatch.GraphWidget(
                    title="CloudFront - Cache Hit Rate",
                    left=[
                        cloudwatch.Metric(
                            namespace="AWS/CloudFront",
                            metric_name="CacheHitRate",
                            statistic="Average",
                            period=Duration.minutes(5)
                        )
                    ],
                    width=6,
                    height=6
                )
            ]
        
        # Add widgets to dashboard
        dashboard.add_widgets(*api_widgets)
        dashboard.add_widgets(*lambda_widgets)
        dashboard.add_widgets(*rds_widgets)
        if cloudfront_widgets:
            dashboard.add_widgets(*cloudfront_widgets)
        
        return dashboard
    
    def _create_application_alarms(self):
        """Create alarms for application-level metrics"""
        
        # API Gateway alarms
        self._create_api_gateway_alarms()
        
        # Lambda function alarms
        self._create_lambda_alarms()
        
        # Database alarms
        self._create_database_alarms()
        
        # Custom application metrics alarms
        self._create_custom_application_alarms()
    
    def _create_api_gateway_alarms(self):
        """Create API Gateway monitoring alarms"""
        
        # High error rate alarm (4xx)
        cloudwatch.Alarm(
            self,
            "APIGateway4xxErrorAlarm",
            alarm_name=f"tutor-api-4xx-errors-{self.env_name}",
            alarm_description="High rate of 4xx client errors in API Gateway",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="4XXError",
                dimensions_map={"ApiName": f"tutor-system-api-{self.env_name}"},
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=50 if self.env_name == "production" else 20,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_actions=[
                cloudwatch_actions.SnsAction(self.alert_topics["warning"])
            ]
        )
        
        # Server error alarm (5xx)
        cloudwatch.Alarm(
            self,
            "APIGateway5xxErrorAlarm",
            alarm_name=f"tutor-api-5xx-errors-{self.env_name}",
            alarm_description="High rate of 5xx server errors in API Gateway",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                dimensions_map={"ApiName": f"tutor-system-api-{self.env_name}"},
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=10 if self.env_name == "production" else 5,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_actions=[
                cloudwatch_actions.SnsAction(self.alert_topics["critical"])
            ]
        )
        
        # High latency alarm
        cloudwatch.Alarm(
            self,
            "APIGatewayLatencyAlarm",
            alarm_name=f"tutor-api-latency-{self.env_name}",
            alarm_description="High API Gateway latency",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Latency",
                dimensions_map={"ApiName": f"tutor-system-api-{self.env_name}"},
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=5000,  # 5 seconds
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_actions=[
                cloudwatch_actions.SnsAction(self.alert_topics["warning"])
            ]
        )
    
    def _create_lambda_alarms(self):
        """Create Lambda function monitoring alarms"""
        
        lambda_functions = [
            "tutor-auth", "tutor-domain-management", "tutor-quiz-engine",
            "tutor-answer-evaluation", "tutor-progress-tracking", "tutor-batch-upload"
        ]
        
        for func in lambda_functions:
            # Error rate alarm
            cloudwatch.Alarm(
                self,
                f"Lambda{func.replace('-', '')}ErrorAlarm",
                alarm_name=f"lambda-{func}-errors-{self.env_name}",
                alarm_description=f"High error rate for {func} Lambda function",
                metric=cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={"FunctionName": f"{func}-{self.env_name}"},
                    statistic="Sum",
                    period=Duration.minutes(5)
                ),
                threshold=5,
                evaluation_periods=2,
                datapoints_to_alarm=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                alarm_actions=[
                    cloudwatch_actions.SnsAction(self.alert_topics["critical"])
                ]
            )
            
            # Duration alarm
            cloudwatch.Alarm(
                self,
                f"Lambda{func.replace('-', '')}DurationAlarm",
                alarm_name=f"lambda-{func}-duration-{self.env_name}",
                alarm_description=f"High duration for {func} Lambda function",
                metric=cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions_map={"FunctionName": f"{func}-{self.env_name}"},
                    statistic="Average",
                    period=Duration.minutes(5)
                ),
                threshold=25000,  # 25 seconds (close to timeout)
                evaluation_periods=3,
                datapoints_to_alarm=2,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                alarm_actions=[
                    cloudwatch_actions.SnsAction(self.alert_topics["warning"])
                ]
            )
            
            # Throttle alarm
            cloudwatch.Alarm(
                self,
                f"Lambda{func.replace('-', '')}ThrottleAlarm",
                alarm_name=f"lambda-{func}-throttles-{self.env_name}",
                alarm_description=f"Throttling detected for {func} Lambda function",
                metric=cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Throttles",
                    dimensions_map={"FunctionName": f"{func}-{self.env_name}"},
                    statistic="Sum",
                    period=Duration.minutes(5)
                ),
                threshold=1,
                evaluation_periods=1,
                datapoints_to_alarm=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                alarm_actions=[
                    cloudwatch_actions.SnsAction(self.alert_topics["critical"])
                ]
            )
    
    def _create_database_alarms(self):
        """Create database monitoring alarms"""
        
        # High ACU utilization
        cloudwatch.Alarm(
            self,
            "AuroraHighACUAlarm",
            alarm_name=f"aurora-high-acu-{self.env_name}",
            alarm_description="High Aurora Serverless ACU utilization",
            metric=cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="ServerlessDatabaseCapacity",
                dimensions_map={"DBClusterIdentifier": f"aurora-cluster-{self.env_name}"},
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=3.5 if self.env_name == "development" else 7.5,  # Near max capacity
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_actions=[
                cloudwatch_actions.SnsAction(self.alert_topics["warning"])
            ]
        )
        
        # High connection count
        cloudwatch.Alarm(
            self,
            "AuroraHighConnectionsAlarm",
            alarm_name=f"aurora-high-connections-{self.env_name}",
            alarm_description="High number of database connections",
            metric=cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="DatabaseConnections",
                dimensions_map={"DBClusterIdentifier": f"aurora-cluster-{self.env_name}"},
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=80,  # Adjust based on expected load
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_actions=[
                cloudwatch_actions.SnsAction(self.alert_topics["warning"])
            ]
        )
    
    def _create_custom_application_alarms(self):
        """Create alarms for custom application metrics"""
        
        # Authentication failure rate
        cloudwatch.Alarm(
            self,
            "AuthFailureRateAlarm",
            alarm_name=f"auth-failure-rate-{self.env_name}",
            alarm_description="High authentication failure rate",
            metric=cloudwatch.Metric(
                namespace="TutorSystem/Security",
                metric_name="AuthenticationFailures",
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=20,
            evaluation_periods=2,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_actions=[
                cloudwatch_actions.SnsAction(self.alert_topics["security"])
            ]
        )
        
        # Rate limiting exceeded
        cloudwatch.Alarm(
            self,
            "RateLimitExceededAlarm",
            alarm_name=f"rate-limit-exceeded-{self.env_name}",
            alarm_description="Rate limiting frequently exceeded",
            metric=cloudwatch.Metric(
                namespace="TutorSystem/Security",
                metric_name="RateLimitExceeded",
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=50,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_actions=[
                cloudwatch_actions.SnsAction(self.alert_topics["security"])
            ]
        )
    
    def _create_infrastructure_alarms(self):
        """Create infrastructure-level monitoring alarms"""
        
        # CloudFormation stack drift detection (production only)
        if self.env_name == "production":
            self._create_drift_detection()
    
    def _create_drift_detection(self):
        """Create CloudFormation stack drift detection"""
        
        # Lambda function for drift detection
        drift_detection_function = _lambda.Function(
            self,
            "DriftDetectionFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=_lambda.Code.from_inline("""
import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cloudformation = boto3.client('cloudformation')
sns = boto3.client('sns')

def lambda_handler(event, context):
    try:
        # List of stacks to check
        stacks_to_check = [
            'TutorSystemStack-production',
            'SecurityMonitoringStack-production',
            'FrontendStack-production'
        ]
        
        drift_detected = False
        drift_details = []
        
        for stack_name in stacks_to_check:
            try:
                # Detect drift
                response = cloudformation.detect_stack_drift(StackName=stack_name)
                drift_detection_id = response['StackDriftDetectionId']
                
                # Wait for detection to complete (simplified)
                import time
                time.sleep(30)
                
                # Get drift results
                drift_result = cloudformation.describe_stack_drift_detection_status(
                    StackDriftDetectionId=drift_detection_id
                )
                
                if drift_result['StackDriftStatus'] == 'DRIFTED':
                    drift_detected = True
                    drift_details.append({
                        'stack': stack_name,
                        'status': drift_result['StackDriftStatus']
                    })
                    
            except Exception as e:
                logger.error(f"Error checking drift for {stack_name}: {str(e)}")
        
        # Send notification if drift detected
        if drift_detected:
            message = {
                'alert': 'CloudFormation Stack Drift Detected',
                'environment': 'production',
                'drifted_stacks': drift_details,
                'timestamp': context.aws_request_id
            }
            
            sns.publish(
                TopicArn=event.get('sns_topic_arn'),
                Subject='🚨 Stack Drift Detected - Production',
                Message=json.dumps(message, indent=2)
            )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'drift_detected': drift_detected,
                'details': drift_details
            })
        }
        
    except Exception as e:
        logger.error(f"Drift detection failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
            """),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "SNS_TOPIC_ARN": self.alert_topics["warning"].topic_arn
            }
        )
        
        # Grant permissions
        drift_detection_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudformation:DetectStackDrift",
                    "cloudformation:DescribeStackDriftDetectionStatus",
                    "cloudformation:ListStacks"
                ],
                resources=["*"]
            )
        )
        
        self.alert_topics["warning"].grant_publish(drift_detection_function)
        
        # Schedule drift detection daily
        events.Rule(
            self,
            "DriftDetectionSchedule",
            schedule=events.Schedule.cron(hour="6", minute="0"),  # 6 AM UTC daily
            targets=[targets.LambdaFunction(drift_detection_function)]
        )
    
    def _create_cost_monitoring(self):
        """Create cost monitoring and budget alerts"""
        
        # Monthly budget
        monthly_limit = 50 if self.env_name == "development" else 200  # USD
        
        budget = budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=f"tutor-system-monthly-budget-{self.env_name}",
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=monthly_limit,
                    unit="USD"
                ),
                cost_filters={
                    "TagKey": ["Environment"],
                    "TagValue": [self.env_name]
                }
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=80,  # 80% of budget
                        threshold_type="PERCENTAGE"
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=self.alert_topics["cost"].topic_arn
                        )
                    ]
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="FORECASTED",
                        comparison_operator="GREATER_THAN",
                        threshold=100,  # 100% of budget
                        threshold_type="PERCENTAGE"
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=self.alert_topics["cost"].topic_arn
                        )
                    ]
                )
            ]
        )
    
    def _create_custom_monitoring(self):
        """Create custom metrics and log monitoring"""
        
        # Log groups for centralized logging
        application_log_group = logs.LogGroup(
            self,
            "ApplicationLogGroup",
            log_group_name=f"/tutor-system/{self.env_name}/application",
            retention=logs.RetentionDays.ONE_MONTH if self.env_name == "development" else logs.RetentionDays.THREE_MONTHS,
            removal_policy=RemovalPolicy.DESTROY if self.env_name == "development" else RemovalPolicy.RETAIN
        )
        
        # Metric filters for error detection
        logs.MetricFilter(
            self,
            "ErrorMetricFilter",
            log_group=application_log_group,
            metric_namespace="TutorSystem/Errors",
            metric_name="ApplicationErrors",
            filter_pattern=logs.FilterPattern.any_term("ERROR", "Exception", "Failed"),
            metric_value="1",
            default_value=0
        )
        
        # Alarm for application errors
        cloudwatch.Alarm(
            self,
            "ApplicationErrorAlarm",
            alarm_name=f"application-errors-{self.env_name}",
            alarm_description="High rate of application errors",
            metric=cloudwatch.Metric(
                namespace="TutorSystem/Errors",
                metric_name="ApplicationErrors",
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=10,
            evaluation_periods=2,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_actions=[
                cloudwatch_actions.SnsAction(self.alert_topics["critical"])
            ]
        )
    
    def _create_incident_response(self):
        """Create automated incident response mechanisms"""
        
        # Auto-scaling response function
        incident_response_function = _lambda.Function(
            self,
            "IncidentResponseFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=_lambda.Code.from_inline("""
import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Parse SNS message
        message = json.loads(event['Records'][0]['Sns']['Message'])
        alarm_name = message.get('AlarmName', '')
        
        logger.info(f"Processing incident response for alarm: {alarm_name}")
        
        # Implement automated responses based on alarm type
        if 'lambda' in alarm_name.lower() and 'throttle' in alarm_name.lower():
            # Increase Lambda concurrency if throttling
            handle_lambda_throttling(alarm_name)
        elif 'aurora' in alarm_name.lower() and 'acu' in alarm_name.lower():
            # Scale up Aurora if needed
            handle_aurora_scaling(alarm_name)
        elif 'api' in alarm_name.lower() and '5xx' in alarm_name.lower():
            # Investigate API Gateway issues
            handle_api_errors(alarm_name)
        
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"Incident response failed: {str(e)}")
        return {'statusCode': 500}

def handle_lambda_throttling(alarm_name):
    # Placeholder for Lambda throttling response
    logger.info(f"Handling Lambda throttling for {alarm_name}")
    # Could implement: increase reserved concurrency, scale out, etc.

def handle_aurora_scaling(alarm_name):
    # Placeholder for Aurora scaling response
    logger.info(f"Handling Aurora scaling for {alarm_name}")
    # Could implement: temporary capacity increase, connection pooling adjustments

def handle_api_errors(alarm_name):
    # Placeholder for API error response
    logger.info(f"Handling API errors for {alarm_name}")
    # Could implement: circuit breaker, fallback responses, etc.
            """),
            timeout=Duration.minutes(2),
            memory_size=256
        )
        
        # Subscribe to critical alerts
        self.alert_topics["critical"].add_subscription(
            sns_subscriptions.LambdaSubscription(incident_response_function)
        )
    
    def _create_outputs(self):
        """Create CloudFormation outputs"""
        cdk.CfnOutput(
            self,
            "DashboardURL",
            value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.dashboard.dashboard_name}",
            description="CloudWatch Dashboard URL"
        )
        
        for topic_name, topic in self.alert_topics.items():
            cdk.CfnOutput(
                self,
                f"{topic_name.title()}AlertsTopicArn",
                value=topic.topic_arn,
                description=f"SNS Topic ARN for {topic_name} alerts"
            )