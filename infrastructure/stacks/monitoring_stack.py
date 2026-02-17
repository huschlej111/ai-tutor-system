"""
Simple Monitoring Stack for Quiz Engine Deployment
Implements Task 6 requirements: CloudWatch monitoring, alarms, logging, and cost budgets
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_budgets as budgets,
    Duration,
)
from constructs import Construct
from typing import Optional


class SimpleMonitoringStack(Stack):
    """Simple monitoring for Quiz Engine and Answer Evaluator with cost tracking"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        backend_stack,  # Add backend stack dependency
        frontend_stack,  # Add frontend stack dependency
        env_name: str,
        notification_email: Optional[str] = None,
        monthly_budget_limit: float = 10.0,  # Default $10/month
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = env_name
        self.notification_email = notification_email
        self.monthly_budget_limit = monthly_budget_limit
        
        # Import Lambda function names from Backend Stack
        self.quiz_engine_function_name = backend_stack.quiz_engine_lambda.function_name
        self.answer_evaluator_function_name = backend_stack.answer_evaluator_lambda.function_name
        
        # Import CloudFront distribution ID from Frontend Stack
        self.distribution_id = frontend_stack.distribution.distribution_id
        
        # Create SNS topic for alerts
        self.alert_topic = sns.Topic(
            self,
            "AlertTopic",
            topic_name=f"tutor-system-alerts-{env_name}",
            display_name=f"Tutor System Alerts - {env_name}"
        )
        
        if notification_email:
            self.alert_topic.add_subscription(
                sns_subs.EmailSubscription(notification_email)
            )
        
        # Create CloudWatch dashboard
        self.dashboard = cloudwatch.Dashboard(
            self,
            "Dashboard",
            dashboard_name=f"TutorSystem-{env_name}"
        )
        
        # Add Lambda metrics to dashboard
        self._add_lambda_metrics()
        
        # Create alarms for critical functions
        self._create_alarms()
        
        # Create cost monitoring and budgets
        self._create_cost_monitoring()
        
        # Output dashboard URL
        cdk.CfnOutput(
            self,
            "DashboardURL",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name=TutorSystem-{env_name}",
            description="CloudWatch Dashboard URL"
        )
        
        cdk.CfnOutput(
            self,
            "AlertTopicArn",
            value=self.alert_topic.topic_arn,
            description="SNS Topic ARN for alerts"
        )
    
    def _add_lambda_metrics(self):
        """Add Lambda function metrics to dashboard"""
        
        # Quiz Engine metrics
        quiz_engine_widget = cloudwatch.GraphWidget(
            title="Quiz Engine Lambda",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions_map={"FunctionName": self.quiz_engine_function_name},
                    statistic="Sum",
                    period=Duration.minutes(5)
                ),
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={"FunctionName": self.quiz_engine_function_name},
                    statistic="Sum",
                    period=Duration.minutes(5)
                )
            ],
            right=[
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions_map={"FunctionName": self.quiz_engine_function_name},
                    statistic="Average",
                    period=Duration.minutes(5)
                )
            ]
        )
        
        # Answer Evaluator metrics
        answer_eval_widget = cloudwatch.GraphWidget(
            title="Answer Evaluator Lambda",
            left=[
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions_map={"FunctionName": self.answer_evaluator_function_name},
                    statistic="Sum",
                    period=Duration.minutes(5)
                ),
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Errors",
                    dimensions_map={"FunctionName": self.answer_evaluator_function_name},
                    statistic="Sum",
                    period=Duration.minutes(5)
                )
            ],
            right=[
                cloudwatch.Metric(
                    namespace="AWS/Lambda",
                    metric_name="Duration",
                    dimensions_map={"FunctionName": self.answer_evaluator_function_name},
                    statistic="Average",
                    period=Duration.minutes(5)
                )
            ]
        )
        
        self.dashboard.add_widgets(quiz_engine_widget, answer_eval_widget)
    
    def _create_alarms(self):
        """Create CloudWatch alarms for critical metrics"""
        
        # Quiz Engine error alarm
        quiz_alarm = cloudwatch.Alarm(
            self,
            "QuizEngineErrorAlarm",
            alarm_name=f"TutorSystem-{self.env_name}-QuizEngine-Errors",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": self.quiz_engine_function_name},
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        quiz_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
        
        # Answer Evaluator error alarm
        eval_alarm = cloudwatch.Alarm(
            self,
            "AnswerEvaluatorErrorAlarm",
            alarm_name=f"TutorSystem-{self.env_name}-AnswerEvaluator-Errors",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Errors",
                dimensions_map={"FunctionName": self.answer_evaluator_function_name},
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
        )
        eval_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))
    
    def _create_cost_monitoring(self):
        """Create AWS Budgets for cost monitoring"""
        
        # Monthly budget with alerts at 80% and 100%
        budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=f"TutorSystem-{self.env_name}-Monthly",
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=self.monthly_budget_limit,
                    unit="USD"
                )
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=80,
                        threshold_type="PERCENTAGE"
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=self.alert_topic.topic_arn
                        )
                    ] if not self.notification_email else [
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL",
                            address=self.notification_email
                        )
                    ]
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=100,
                        threshold_type="PERCENTAGE"
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=self.alert_topic.topic_arn
                        )
                    ] if not self.notification_email else [
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL",
                            address=self.notification_email
                        )
                    ]
                )
            ]
        )
        
        cdk.CfnOutput(
            self,
            "MonthlyBudgetLimit",
            value=f"${self.monthly_budget_limit}",
            description="Monthly budget limit (alerts at 80% and 100%)"
        )
