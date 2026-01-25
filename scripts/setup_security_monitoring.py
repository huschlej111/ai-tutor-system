#!/usr/bin/env python3
"""
Security monitoring setup script for Know-It-All Tutor System.
Configures additional AWS security services and monitoring.
"""

import argparse
import boto3
import json
import sys
from typing import Dict, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError


class SecurityMonitoringSetup:
    """Sets up comprehensive AWS security monitoring for the tutor system."""
    
    def __init__(self, region: str = "us-east-1", environment: str = "development"):
        self.region = region
        self.environment = environment
        
        # Initialize AWS clients
        try:
            self.cloudtrail_client = boto3.client('cloudtrail', region_name=region)
            self.guardduty_client = boto3.client('guardduty', region_name=region)
            self.config_client = boto3.client('config', region_name=region)
            self.cloudwatch_client = boto3.client('cloudwatch', region_name=region)
            self.sns_client = boto3.client('sns', region_name=region)
            self.iam_client = boto3.client('iam', region_name=region)
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
    
    def setup_cloudtrail_insights(self) -> bool:
        """Enable CloudTrail Insights for anomaly detection."""
        print("🔍 Setting up CloudTrail Insights...")
        
        try:
            trail_name = f"tutor-system-security-trail-{self.environment}"
            
            # Enable CloudTrail Insights
            self.cloudtrail_client.put_insight_selectors(
                TrailName=trail_name,
                InsightSelectors=[
                    {
                        'InsightType': 'ApiCallRateInsight'
                    }
                ]
            )
            
            print("✅ CloudTrail Insights enabled successfully")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'TrailNotFoundException':
                print("⚠️  CloudTrail not found. Deploy the CDK stack first.")
                return False
            else:
                print(f"❌ Error enabling CloudTrail Insights: {e}")
                return False
    
    def setup_guardduty_members(self, member_accounts: List[str] = None) -> bool:
        """Set up GuardDuty member accounts if in a multi-account setup."""
        print("🛡️  Setting up GuardDuty configuration...")
        
        try:
            # Get detector ID
            detectors = self.guardduty_client.list_detectors()
            if not detectors['DetectorIds']:
                print("⚠️  GuardDuty detector not found. Deploy the CDK stack first.")
                return False
            
            detector_id = detectors['DetectorIds'][0]
            
            # Enable S3 protection
            self.guardduty_client.update_detector(
                DetectorId=detector_id,
                DataSources={
                    'S3Logs': {
                        'Enable': True
                    }
                }
            )
            
            # Set finding publishing frequency
            self.guardduty_client.update_detector(
                DetectorId=detector_id,
                FindingPublishingFrequency='FIFTEEN_MINUTES'
            )
            
            print("✅ GuardDuty configuration updated successfully")
            return True
            
        except ClientError as e:
            print(f"❌ Error configuring GuardDuty: {e}")
            return False
    
    def setup_config_remediation(self) -> bool:
        """Set up AWS Config remediation configurations."""
        print("⚙️  Setting up Config remediation...")
        
        try:
            # Create remediation configuration for S3 bucket public access
            self.config_client.put_remediation_configurations(
                RemediationConfigurations=[
                    {
                        'ConfigRuleName': 's3-bucket-public-access-prohibited',
                        'TargetType': 'SSM_DOCUMENT',
                        'TargetId': 'AWSConfigRemediation-RemoveS3BucketPublicAccess',
                        'TargetVersion': '1',
                        'Parameters': {
                            'AutomationAssumeRole': {
                                'StaticValue': {
                                    'Values': [
                                        f'arn:aws:iam::{self.account_id}:role/aws-config-role'
                                    ]
                                }
                            },
                            'S3BucketName': {
                                'ResourceValue': {
                                    'Value': 'RESOURCE_ID'
                                }
                            }
                        },
                        'ResourceType': 'AWS::S3::Bucket',
                        'Automatic': False,  # Manual approval required
                        'ExecutionControls': {
                            'SsmControls': {
                                'ConcurrentExecutionRatePercentage': 10,
                                'ErrorPercentage': 10
                            }
                        }
                    }
                ]
            )
            
            print("✅ Config remediation configurations created successfully")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchConfigRuleException':
                print("⚠️  Config rules not found. Deploy the CDK stack first.")
                return False
            else:
                print(f"❌ Error setting up Config remediation: {e}")
                return False
    
    def setup_custom_metrics(self) -> bool:
        """Set up custom CloudWatch metrics for security monitoring."""
        print("📊 Setting up custom security metrics...")
        
        try:
            # Create custom metric filters for CloudTrail logs
            log_group_name = f"/aws/cloudtrail/tutor-system-{self.environment}"
            
            # Metric filter for root account usage
            self.cloudwatch_client.put_metric_filter(
                logGroupName=log_group_name,
                filterName="RootAccountUsage",
                filterPattern='{ ($.userIdentity.type = "Root") && ($.userIdentity.invokedBy NOT EXISTS) && ($.eventType != "AwsServiceEvent") }',
                metricTransformations=[
                    {
                        'metricName': 'RootAccountUsageCount',
                        'metricNamespace': 'TutorSystem/Security',
                        'metricValue': '1',
                        'defaultValue': 0
                    }
                ]
            )
            
            # Metric filter for unauthorized API calls
            self.cloudwatch_client.put_metric_filter(
                logGroupName=log_group_name,
                filterName="UnauthorizedAPICalls",
                filterPattern='{ ($.errorCode = "*UnauthorizedOperation") || ($.errorCode = "AccessDenied*") }',
                metricTransformations=[
                    {
                        'metricName': 'UnauthorizedAPICallsCount',
                        'metricNamespace': 'TutorSystem/Security',
                        'metricValue': '1',
                        'defaultValue': 0
                    }
                ]
            )
            
            # Metric filter for IAM policy changes
            self.cloudwatch_client.put_metric_filter(
                logGroupName=log_group_name,
                filterName="IAMPolicyChanges",
                filterPattern='{ ($.eventName=DeleteGroupPolicy) || ($.eventName=DeleteRolePolicy) || ($.eventName=DeleteUserPolicy) || ($.eventName=PutGroupPolicy) || ($.eventName=PutRolePolicy) || ($.eventName=PutUserPolicy) || ($.eventName=CreatePolicy) || ($.eventName=DeletePolicy) || ($.eventName=CreatePolicyVersion) || ($.eventName=DeletePolicyVersion) || ($.eventName=AttachRolePolicy) || ($.eventName=DetachRolePolicy) || ($.eventName=AttachUserPolicy) || ($.eventName=DetachUserPolicy) || ($.eventName=AttachGroupPolicy) || ($.eventName=DetachGroupPolicy) }',
                metricTransformations=[
                    {
                        'metricName': 'IAMPolicyChangesCount',
                        'metricNamespace': 'TutorSystem/Security',
                        'metricValue': '1',
                        'defaultValue': 0
                    }
                ]
            )
            
            print("✅ Custom security metrics created successfully")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("⚠️  CloudTrail log group not found. Deploy the CDK stack first.")
                return False
            else:
                print(f"❌ Error creating custom metrics: {e}")
                return False
    
    def setup_security_dashboard(self) -> bool:
        """Create a CloudWatch dashboard for security monitoring."""
        print("📈 Setting up security monitoring dashboard...")
        
        try:
            dashboard_body = {
                "widgets": [
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                ["TutorSystem/Security", "RootAccountUsageCount"],
                                [".", "UnauthorizedAPICallsCount"],
                                [".", "IAMPolicyChangesCount"]
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": self.region,
                            "title": "Security Events",
                            "yAxis": {
                                "left": {
                                    "min": 0
                                }
                            }
                        }
                    },
                    {
                        "type": "metric",
                        "x": 12,
                        "y": 0,
                        "width": 12,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                ["AWS/ApiGateway", "4XXError", "ApiName", f"tutor-system-api-{self.environment}"],
                                [".", "5XXError", ".", "."],
                                [".", "Count", ".", "."]
                            ],
                            "period": 300,
                            "stat": "Sum",
                            "region": self.region,
                            "title": "API Gateway Metrics"
                        }
                    },
                    {
                        "type": "metric",
                        "x": 0,
                        "y": 6,
                        "width": 24,
                        "height": 6,
                        "properties": {
                            "metrics": [
                                ["AWS/Lambda", "Errors"],
                                [".", "Duration"],
                                [".", "Throttles"]
                            ],
                            "period": 300,
                            "stat": "Average",
                            "region": self.region,
                            "title": "Lambda Function Metrics"
                        }
                    }
                ]
            }
            
            self.cloudwatch_client.put_dashboard(
                DashboardName=f"TutorSystem-Security-{self.environment}",
                DashboardBody=json.dumps(dashboard_body)
            )
            
            print("✅ Security monitoring dashboard created successfully")
            return True
            
        except ClientError as e:
            print(f"❌ Error creating security dashboard: {e}")
            return False
    
    def validate_security_setup(self) -> Dict[str, bool]:
        """Validate that all security monitoring components are properly configured."""
        print("🔍 Validating security monitoring setup...")
        
        results = {}
        
        # Check CloudTrail
        try:
            trails = self.cloudtrail_client.describe_trails()
            trail_exists = any(
                f"tutor-system-security-trail-{self.environment}" in trail['Name']
                for trail in trails['trailList']
            )
            results['cloudtrail'] = trail_exists
        except ClientError:
            results['cloudtrail'] = False
        
        # Check GuardDuty
        try:
            detectors = self.guardduty_client.list_detectors()
            results['guardduty'] = len(detectors['DetectorIds']) > 0
        except ClientError:
            results['guardduty'] = False
        
        # Check Config
        try:
            recorders = self.config_client.describe_configuration_recorders()
            results['config'] = len(recorders['ConfigurationRecorders']) > 0
        except ClientError:
            results['config'] = False
        
        # Check SNS topic
        try:
            topics = self.sns_client.list_topics()
            topic_exists = any(
                f"tutor-system-security-alerts-{self.environment}" in topic['TopicArn']
                for topic in topics['Topics']
            )
            results['sns_alerts'] = topic_exists
        except ClientError:
            results['sns_alerts'] = False
        
        # Print validation results
        print("\n📋 Security Monitoring Validation Results:")
        for service, status in results.items():
            status_icon = "✅" if status else "❌"
            print(f"   {service}: {status_icon}")
        
        return results
    
    def run_full_setup(self) -> bool:
        """Run the complete security monitoring setup."""
        print(f"🚀 Setting up security monitoring for environment: {self.environment}")
        print(f"📍 Region: {self.region}")
        print(f"🏢 Account: {self.account_id}")
        print("-" * 60)
        
        success_count = 0
        total_steps = 5
        
        # Step 1: CloudTrail Insights
        if self.setup_cloudtrail_insights():
            success_count += 1
        
        # Step 2: GuardDuty configuration
        if self.setup_guardduty_members():
            success_count += 1
        
        # Step 3: Config remediation
        if self.setup_config_remediation():
            success_count += 1
        
        # Step 4: Custom metrics
        if self.setup_custom_metrics():
            success_count += 1
        
        # Step 5: Security dashboard
        if self.setup_security_dashboard():
            success_count += 1
        
        print(f"\n📊 Setup completed: {success_count}/{total_steps} steps successful")
        
        # Validate setup
        validation_results = self.validate_security_setup()
        all_valid = all(validation_results.values())
        
        if all_valid:
            print("\n🎉 Security monitoring setup completed successfully!")
            print("📈 Access your security dashboard in the CloudWatch console")
            print("🔔 Security alerts will be sent to the configured SNS topic")
        else:
            print("\n⚠️  Some components may need manual configuration")
            print("📖 Check the CDK deployment and AWS console for details")
        
        return success_count == total_steps and all_valid


def main():
    """Main entry point for the security monitoring setup script."""
    parser = argparse.ArgumentParser(
        description="Set up AWS security monitoring for Know-It-All Tutor System"
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
    
    args = parser.parse_args()
    
    # Create setup instance
    setup = SecurityMonitoringSetup(
        region=args.region,
        environment=args.environment
    )
    
    if args.validate_only:
        # Only run validation
        results = setup.validate_security_setup()
        success = all(results.values())
        sys.exit(0 if success else 1)
    else:
        # Run full setup
        success = setup.run_full_setup()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()