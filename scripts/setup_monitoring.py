#!/usr/bin/env python3
"""
Monitoring Setup Script for Know-It-All Tutor System
Configures CloudWatch monitoring, alarms, and dashboards
"""
import boto3
import json
import argparse
import sys
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class MonitoringSetup:
    """Handles setup and configuration of monitoring infrastructure"""
    
    def __init__(self, environment: str, region: str = "us-east-1"):
        self.environment = environment
        self.region = region
        
        # Initialize AWS clients
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.logs = boto3.client('logs', region_name=region)
        self.budgets = boto3.client('budgets', region_name=region)
    
    def setup_all(self) -> bool:
        """Set up all monitoring components"""
        print(f"🔧 Setting up monitoring for {self.environment} environment...")
        
        try:
            # Create custom metrics
            self._create_custom_metrics()
            
            # Set up log retention policies
            self._configure_log_retention()
            
            # Create metric filters
            self._create_metric_filters()
            
            # Validate alarm configuration
            self._validate_alarms()
            
            # Set up cost monitoring
            self._setup_cost_monitoring()
            
            # Create monitoring reports
            self._create_monitoring_reports()
            
            print("✅ Monitoring setup completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Monitoring setup failed: {str(e)}")
            return False
    
    def _create_custom_metrics(self):
        """Create custom CloudWatch metrics"""
        print("📊 Creating custom metrics...")
        
        # Create namespace for application metrics
        namespace = "TutorSystem/Application"
        
        # Sample metrics to initialize the namespace
        sample_metrics = [
            {
                'MetricName': 'UserRegistrations',
                'Value': 0,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'QuizCompletions',
                'Value': 0,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'DomainCreations',
                'Value': 0,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'AnswerEvaluations',
                'Value': 0,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }
        ]
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=sample_metrics
            )
            print(f"✅ Created custom metrics in namespace: {namespace}")
            
        except Exception as e:
            print(f"❌ Failed to create custom metrics: {str(e)}")
    
    def _configure_log_retention(self):
        """Configure log retention policies for all log groups"""
        print("📝 Configuring log retention policies...")
        
        # Define retention periods by environment
        retention_days = 30 if self.environment == "development" else 90
        
        # Log groups to configure
        log_groups = [
            f"/aws/lambda/tutor-auth-{self.environment}",
            f"/aws/lambda/tutor-domain-management-{self.environment}",
            f"/aws/lambda/tutor-quiz-engine-{self.environment}",
            f"/aws/lambda/tutor-answer-evaluation-{self.environment}",
            f"/aws/lambda/tutor-progress-tracking-{self.environment}",
            f"/aws/lambda/tutor-batch-upload-{self.environment}",
            f"/aws/apigateway/tutor-system-{self.environment}",
            f"/tutor-system/{self.environment}/application"
        ]
        
        for log_group in log_groups:
            try:
                # Check if log group exists
                self.logs.describe_log_groups(logGroupNamePrefix=log_group)
                
                # Set retention policy
                self.logs.put_retention_policy(
                    logGroupName=log_group,
                    retentionInDays=retention_days
                )
                print(f"✅ Set retention policy for {log_group}: {retention_days} days")
                
            except self.logs.exceptions.ResourceNotFoundException:
                print(f"⚠️ Log group not found: {log_group}")
            except Exception as e:
                print(f"❌ Failed to set retention for {log_group}: {str(e)}")
    
    def _create_metric_filters(self):
        """Create CloudWatch metric filters for log analysis"""
        print("🔍 Creating metric filters...")
        
        # Define metric filters
        filters = [
            {
                'log_group': f"/aws/lambda/tutor-auth-{self.environment}",
                'filter_name': f"AuthenticationErrors-{self.environment}",
                'filter_pattern': '[timestamp, request_id, level="ERROR", ...]',
                'metric_namespace': 'TutorSystem/Security',
                'metric_name': 'AuthenticationErrors',
                'metric_value': '1'
            },
            {
                'log_group': f"/aws/lambda/tutor-quiz-engine-{self.environment}",
                'filter_name': f"QuizEngineErrors-{self.environment}",
                'filter_pattern': '[timestamp, request_id, level="ERROR", ...]',
                'metric_namespace': 'TutorSystem/Application',
                'metric_name': 'QuizEngineErrors',
                'metric_value': '1'
            },
            {
                'log_group': f"/aws/apigateway/tutor-system-{self.environment}",
                'filter_name': f"APIGatewayErrors-{self.environment}",
                'filter_pattern': '[..., status_code>=400]',
                'metric_namespace': 'TutorSystem/API',
                'metric_name': 'APIErrors',
                'metric_value': '1'
            }
        ]
        
        for filter_config in filters:
            try:
                # Check if log group exists
                self.logs.describe_log_groups(
                    logGroupNamePrefix=filter_config['log_group']
                )
                
                # Create metric filter
                self.logs.put_metric_filter(
                    logGroupName=filter_config['log_group'],
                    filterName=filter_config['filter_name'],
                    filterPattern=filter_config['filter_pattern'],
                    metricTransformations=[
                        {
                            'metricName': filter_config['metric_name'],
                            'metricNamespace': filter_config['metric_namespace'],
                            'metricValue': filter_config['metric_value'],
                            'defaultValue': 0
                        }
                    ]
                )
                print(f"✅ Created metric filter: {filter_config['filter_name']}")
                
            except self.logs.exceptions.ResourceNotFoundException:
                print(f"⚠️ Log group not found: {filter_config['log_group']}")
            except Exception as e:
                print(f"❌ Failed to create metric filter {filter_config['filter_name']}: {str(e)}")
    
    def _validate_alarms(self):
        """Validate that all required alarms are configured"""
        print("🚨 Validating alarm configuration...")
        
        # List all alarms for this environment
        try:
            response = self.cloudwatch.describe_alarms(
                AlarmNamePrefix=f"tutor-"
            )
            
            alarms = response.get('MetricAlarms', [])
            environment_alarms = [
                alarm for alarm in alarms 
                if self.environment in alarm['AlarmName']
            ]
            
            print(f"📊 Found {len(environment_alarms)} alarms for {self.environment} environment:")
            
            for alarm in environment_alarms:
                state = alarm['StateValue']
                state_emoji = "✅" if state == "OK" else "⚠️" if state == "INSUFFICIENT_DATA" else "🚨"
                print(f"  {state_emoji} {alarm['AlarmName']}: {state}")
            
            # Check for critical alarms
            critical_alarms = [
                f"tutor-api-5xx-errors-{self.environment}",
                f"lambda-tutor-auth-errors-{self.environment}",
                f"aurora-high-connections-{self.environment}"
            ]
            
            missing_alarms = []
            for critical_alarm in critical_alarms:
                if not any(alarm['AlarmName'] == critical_alarm for alarm in environment_alarms):
                    missing_alarms.append(critical_alarm)
            
            if missing_alarms:
                print(f"⚠️ Missing critical alarms: {', '.join(missing_alarms)}")
            else:
                print("✅ All critical alarms are configured")
                
        except Exception as e:
            print(f"❌ Failed to validate alarms: {str(e)}")
    
    def _setup_cost_monitoring(self):
        """Set up cost monitoring and budget alerts"""
        print("💰 Setting up cost monitoring...")
        
        try:
            # Get account ID
            sts = boto3.client('sts')
            account_id = sts.get_caller_identity()['Account']
            
            # Check if budget exists
            budget_name = f"tutor-system-monthly-budget-{self.environment}"
            
            try:
                self.budgets.describe_budget(
                    AccountId=account_id,
                    BudgetName=budget_name
                )
                print(f"✅ Budget already exists: {budget_name}")
                
            except self.budgets.exceptions.NotFoundException:
                print(f"⚠️ Budget not found: {budget_name}")
                print("   Budget should be created via CDK deployment")
            
        except Exception as e:
            print(f"❌ Failed to check cost monitoring: {str(e)}")
    
    def _create_monitoring_reports(self):
        """Create monitoring reports and summaries"""
        print("📋 Creating monitoring reports...")
        
        try:
            # Get current metrics summary
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            # API Gateway metrics
            api_metrics = self._get_metric_statistics(
                namespace="AWS/ApiGateway",
                metric_name="Count",
                dimensions=[{"Name": "ApiName", "Value": f"tutor-system-api-{self.environment}"}],
                start_time=start_time,
                end_time=end_time,
                period=3600,
                statistics=["Sum"]
            )
            
            # Lambda metrics
            lambda_metrics = {}
            lambda_functions = [
                "tutor-auth", "tutor-domain-management", "tutor-quiz-engine",
                "tutor-answer-evaluation", "tutor-progress-tracking", "tutor-batch-upload"
            ]
            
            for func in lambda_functions:
                lambda_metrics[func] = self._get_metric_statistics(
                    namespace="AWS/Lambda",
                    metric_name="Invocations",
                    dimensions=[{"Name": "FunctionName", "Value": f"{func}-{self.environment}"}],
                    start_time=start_time,
                    end_time=end_time,
                    period=3600,
                    statistics=["Sum"]
                )
            
            # Create summary report
            report = {
                "environment": self.environment,
                "report_time": end_time.isoformat(),
                "period": "24_hours",
                "api_gateway": {
                    "total_requests": sum(point['Sum'] for point in api_metrics.get('Datapoints', [])),
                    "datapoints": len(api_metrics.get('Datapoints', []))
                },
                "lambda_functions": {
                    func: {
                        "total_invocations": sum(point['Sum'] for point in metrics.get('Datapoints', [])),
                        "datapoints": len(metrics.get('Datapoints', []))
                    }
                    for func, metrics in lambda_metrics.items()
                }
            }
            
            # Save report
            report_file = f"monitoring-report-{self.environment}-{end_time.strftime('%Y%m%d')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, indent=2, fp=f)
            
            print(f"✅ Created monitoring report: {report_file}")
            
            # Print summary
            print("\n📊 24-Hour Monitoring Summary:")
            print(f"   API Requests: {report['api_gateway']['total_requests']}")
            for func, data in report['lambda_functions'].items():
                print(f"   {func}: {data['total_invocations']} invocations")
            
        except Exception as e:
            print(f"❌ Failed to create monitoring reports: {str(e)}")
    
    def _get_metric_statistics(self, namespace: str, metric_name: str, dimensions: List[Dict], 
                              start_time: datetime, end_time: datetime, period: int, 
                              statistics: List[str]) -> Dict:
        """Get CloudWatch metric statistics"""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=statistics
            )
            return response
            
        except Exception as e:
            print(f"⚠️ Failed to get metrics for {namespace}/{metric_name}: {str(e)}")
            return {}
    
    def test_alerts(self) -> bool:
        """Test alert system by sending test notifications"""
        print("🧪 Testing alert system...")
        
        try:
            # Find SNS topics for this environment
            response = self.sns.list_topics()
            topics = response.get('Topics', [])
            
            environment_topics = [
                topic for topic in topics 
                if self.environment in topic['TopicArn']
            ]
            
            if not environment_topics:
                print(f"⚠️ No SNS topics found for {self.environment} environment")
                return False
            
            # Send test message to warning topic
            warning_topic = None
            for topic in environment_topics:
                if 'warning' in topic['TopicArn']:
                    warning_topic = topic['TopicArn']
                    break
            
            if warning_topic:
                test_message = {
                    "test": True,
                    "environment": self.environment,
                    "message": "This is a test alert from the monitoring setup script",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                self.sns.publish(
                    TopicArn=warning_topic,
                    Subject=f"🧪 Test Alert - {self.environment.title()} Environment",
                    Message=json.dumps(test_message, indent=2)
                )
                
                print(f"✅ Test alert sent to: {warning_topic}")
                return True
            else:
                print("⚠️ Warning topic not found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to test alerts: {str(e)}")
            return False


def main():
    """Main monitoring setup script entry point"""
    parser = argparse.ArgumentParser(description="Set up monitoring for Know-It-All Tutor System")
    parser.add_argument(
        "environment",
        choices=["development", "production"],
        help="Target environment"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--test-alerts",
        action="store_true",
        help="Send test alerts to verify notification system"
    )
    
    args = parser.parse_args()
    
    # Create monitoring setup instance
    monitoring = MonitoringSetup(
        environment=args.environment,
        region=args.region
    )
    
    # Run setup
    success = monitoring.setup_all()
    
    # Test alerts if requested
    if args.test_alerts and success:
        monitoring.test_alerts()
    
    if success:
        print(f"\n🎉 Monitoring setup for {args.environment} completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Monitoring setup for {args.environment} failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()