"""
Deployment Validation Tests for Know-It-All Tutor System
Tests infrastructure provisioning, health checks, and rollback procedures
"""
import pytest
import boto3
import requests
import json
import time
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from moto import mock_aws
import os


class DeploymentValidator:
    """Validates deployment infrastructure and functionality"""
    
    def __init__(self, environment: str, region: str = "us-east-1"):
        self.environment = environment
        self.region = region
        
        # Initialize AWS clients
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.apigateway = boto3.client('apigateway', region_name=region)
        self.rds = boto3.client('rds', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.cognito = boto3.client('cognito-idp', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        # Stack names
        self.stack_names = [
            f"SecurityMonitoringStack-{environment}",
            f"PipelineStack-{environment}",
            f"TutorSystemStack-{environment}",
            f"FrontendStack-{environment}",
            f"MonitoringStack-{environment}"
        ]
    
    def validate_all(self) -> Dict[str, Any]:
        """Run all deployment validation tests"""
        results = {
            "environment": self.environment,
            "validation_time": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        # Infrastructure validation
        results["tests"]["infrastructure"] = self.validate_infrastructure()
        
        # Service health validation
        results["tests"]["health_checks"] = self.validate_service_health()
        
        # Security validation
        results["tests"]["security"] = self.validate_security_configuration()
        
        # Performance validation
        results["tests"]["performance"] = self.validate_performance()
        
        # Monitoring validation
        results["tests"]["monitoring"] = self.validate_monitoring()
        
        # Integration validation
        results["tests"]["integration"] = self.validate_integration()
        
        # Calculate overall status
        all_passed = all(
            test_result.get("status") == "PASS" 
            for test_result in results["tests"].values()
        )
        results["overall_status"] = "PASS" if all_passed else "FAIL"
        
        return results
    
    def validate_infrastructure(self) -> Dict[str, Any]:
        """Validate CloudFormation stacks and resources"""
        print("🏗️ Validating infrastructure...")
        
        result = {
            "status": "PASS",
            "details": {},
            "errors": []
        }
        
        try:
            # Check all stacks exist and are in good state
            for stack_name in self.stack_names:
                try:
                    response = self.cloudformation.describe_stacks(StackName=stack_name)
                    stack = response['Stacks'][0]
                    
                    stack_status = stack['StackStatus']
                    result["details"][stack_name] = {
                        "status": stack_status,
                        "creation_time": stack['CreationTime'].isoformat(),
                        "outputs": {
                            output['OutputKey']: output['OutputValue']
                            for output in stack.get('Outputs', [])
                        }
                    }
                    
                    # Check if stack is in a healthy state
                    if not stack_status.endswith('_COMPLETE'):
                        result["status"] = "FAIL"
                        result["errors"].append(f"Stack {stack_name} is in unhealthy state: {stack_status}")
                    
                except self.cloudformation.exceptions.ClientError as e:
                    if 'does not exist' in str(e):
                        result["status"] = "FAIL"
                        result["errors"].append(f"Stack {stack_name} does not exist")
                    else:
                        raise
            
            # Validate key resources exist
            self._validate_key_resources(result)
            
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Infrastructure validation failed: {str(e)}")
        
        return result
    
    def _validate_key_resources(self, result: Dict[str, Any]):
        """Validate that key AWS resources exist and are configured correctly"""
        
        # Check Lambda functions
        expected_functions = [
            f"tutor-auth-{self.environment}",
            f"tutor-domain-management-{self.environment}",
            f"tutor-quiz-engine-{self.environment}",
            f"tutor-answer-evaluation-{self.environment}",
            f"tutor-progress-tracking-{self.environment}",
            f"tutor-batch-upload-{self.environment}"
        ]
        
        for function_name in expected_functions:
            try:
                self.lambda_client.get_function(FunctionName=function_name)
                result["details"][f"lambda_{function_name}"] = "EXISTS"
            except self.lambda_client.exceptions.ResourceNotFoundException:
                result["status"] = "FAIL"
                result["errors"].append(f"Lambda function {function_name} not found")
        
        # Check API Gateway
        try:
            apis = self.apigateway.get_rest_apis()
            api_names = [api['name'] for api in apis['items']]
            expected_api = f"tutor-system-api-{self.environment}"
            
            if expected_api in api_names:
                result["details"]["api_gateway"] = "EXISTS"
            else:
                result["status"] = "FAIL"
                result["errors"].append(f"API Gateway {expected_api} not found")
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"API Gateway validation failed: {str(e)}")
        
        # Check RDS cluster
        try:
            clusters = self.rds.describe_db_clusters()
            cluster_ids = [cluster['DBClusterIdentifier'] for cluster in clusters['DBClusters']]
            expected_cluster = f"aurora-cluster-{self.environment}"
            
            if any(expected_cluster in cluster_id for cluster_id in cluster_ids):
                result["details"]["rds_cluster"] = "EXISTS"
            else:
                result["status"] = "FAIL"
                result["errors"].append(f"RDS cluster {expected_cluster} not found")
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"RDS validation failed: {str(e)}")
        
        # Check Cognito User Pool
        try:
            user_pools = self.cognito.list_user_pools(MaxResults=50)
            pool_names = [pool['Name'] for pool in user_pools['UserPools']]
            expected_pool = f"know-it-all-tutor-users-{self.environment}"
            
            if expected_pool in pool_names:
                result["details"]["cognito_user_pool"] = "EXISTS"
            else:
                result["status"] = "FAIL"
                result["errors"].append(f"Cognito User Pool {expected_pool} not found")
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Cognito validation failed: {str(e)}")
    
    def validate_service_health(self) -> Dict[str, Any]:
        """Validate that all services are healthy and responding"""
        print("🏥 Validating service health...")
        
        result = {
            "status": "PASS",
            "details": {},
            "errors": []
        }
        
        try:
            # Get API Gateway URL from CloudFormation outputs
            api_url = self._get_stack_output("TutorSystemStack", "APIGatewayURL")
            
            if not api_url:
                result["status"] = "FAIL"
                result["errors"].append("Could not get API Gateway URL")
                return result
            
            # Test health endpoint
            health_check = self._test_endpoint(f"{api_url}health", method="GET")
            result["details"]["health_endpoint"] = health_check
            
            if not health_check["success"]:
                result["status"] = "FAIL"
                result["errors"].append("Health endpoint check failed")
            
            # Test authentication endpoints (should return proper error codes)
            auth_endpoints = [
                ("auth/login", "POST"),
                ("auth/register", "POST")
            ]
            
            for endpoint, method in auth_endpoints:
                endpoint_result = self._test_endpoint(f"{api_url}{endpoint}", method=method, expect_error=True)
                result["details"][f"auth_{endpoint.replace('/', '_')}"] = endpoint_result
                
                # These should return 400 (bad request) for empty body, not 500
                if endpoint_result["status_code"] == 500:
                    result["status"] = "FAIL"
                    result["errors"].append(f"Auth endpoint {endpoint} returning 500 error")
            
            # Test protected endpoints (should return 401 without auth)
            protected_endpoints = [
                ("domains", "GET"),
                ("quiz/start", "POST"),
                ("progress/dashboard", "GET")
            ]
            
            for endpoint, method in protected_endpoints:
                endpoint_result = self._test_endpoint(f"{api_url}{endpoint}", method=method, expect_error=True)
                result["details"][f"protected_{endpoint.replace('/', '_')}"] = endpoint_result
                
                # Should return 401 (unauthorized) without proper auth
                if endpoint_result["status_code"] not in [401, 403]:
                    result["status"] = "FAIL"
                    result["errors"].append(f"Protected endpoint {endpoint} not properly secured")
            
            # Test frontend accessibility
            frontend_url = self._get_stack_output("FrontendStack", "FrontendURL")
            if frontend_url:
                frontend_check = self._test_endpoint(frontend_url, method="GET")
                result["details"]["frontend"] = frontend_check
                
                if not frontend_check["success"]:
                    result["status"] = "FAIL"
                    result["errors"].append("Frontend accessibility check failed")
            
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Service health validation failed: {str(e)}")
        
        return result
    
    def _test_endpoint(self, url: str, method: str = "GET", expect_error: bool = False, timeout: int = 30) -> Dict[str, Any]:
        """Test an HTTP endpoint"""
        try:
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json={}, timeout=timeout)
            else:
                response = requests.request(method, url, timeout=timeout)
            
            success = (200 <= response.status_code < 300) or (expect_error and 400 <= response.status_code < 500)
            
            return {
                "success": success,
                "status_code": response.status_code,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "headers": dict(response.headers),
                "url": url
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def validate_security_configuration(self) -> Dict[str, Any]:
        """Validate security configurations"""
        print("🔒 Validating security configuration...")
        
        result = {
            "status": "PASS",
            "details": {},
            "errors": []
        }
        
        try:
            # Check API Gateway security headers
            api_url = self._get_stack_output("TutorSystemStack", "APIGatewayURL")
            if api_url:
                health_response = self._test_endpoint(f"{api_url}health")
                if health_response.get("success"):
                    headers = health_response.get("headers", {})
                    
                    # Check for security headers
                    security_headers = [
                        "Strict-Transport-Security",
                        "X-Content-Type-Options",
                        "X-Frame-Options",
                        "X-XSS-Protection"
                    ]
                    
                    missing_headers = []
                    for header in security_headers:
                        if header not in headers:
                            missing_headers.append(header)
                    
                    result["details"]["security_headers"] = {
                        "present": [h for h in security_headers if h in headers],
                        "missing": missing_headers
                    }
                    
                    if missing_headers:
                        result["status"] = "FAIL"
                        result["errors"].append(f"Missing security headers: {', '.join(missing_headers)}")
            
            # Check HTTPS enforcement
            if api_url and api_url.startswith("https://"):
                result["details"]["https_enforcement"] = "ENABLED"
            else:
                result["status"] = "FAIL"
                result["errors"].append("HTTPS not enforced on API Gateway")
            
            # Check Cognito configuration
            user_pool_id = self._get_stack_output("TutorSystemStack", "UserPoolId")
            if user_pool_id:
                try:
                    user_pool = self.cognito.describe_user_pool(UserPoolId=user_pool_id)
                    pool_config = user_pool['UserPool']
                    
                    # Check password policy
                    password_policy = pool_config.get('Policies', {}).get('PasswordPolicy', {})
                    result["details"]["password_policy"] = {
                        "min_length": password_policy.get('MinimumLength', 0),
                        "require_uppercase": password_policy.get('RequireUppercase', False),
                        "require_lowercase": password_policy.get('RequireLowercase', False),
                        "require_numbers": password_policy.get('RequireNumbers', False),
                        "require_symbols": password_policy.get('RequireSymbols', False)
                    }
                    
                    # Validate password policy strength
                    if password_policy.get('MinimumLength', 0) < 8:
                        result["status"] = "FAIL"
                        result["errors"].append("Password minimum length is too weak")
                    
                    # Check MFA configuration
                    mfa_config = pool_config.get('MfaConfiguration', 'OFF')
                    result["details"]["mfa_configuration"] = mfa_config
                    
                    if self.environment == "production" and mfa_config == "OFF":
                        result["status"] = "FAIL"
                        result["errors"].append("MFA should be enabled in production")
                
                except Exception as e:
                    result["errors"].append(f"Cognito security validation failed: {str(e)}")
            
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Security validation failed: {str(e)}")
        
        return result
    
    def validate_performance(self) -> Dict[str, Any]:
        """Validate performance characteristics"""
        print("⚡ Validating performance...")
        
        result = {
            "status": "PASS",
            "details": {},
            "errors": []
        }
        
        try:
            # Test API response times
            api_url = self._get_stack_output("TutorSystemStack", "APIGatewayURL")
            if api_url:
                # Test health endpoint performance
                response_times = []
                for i in range(5):  # Test 5 times
                    health_check = self._test_endpoint(f"{api_url}health")
                    if health_check.get("success"):
                        response_times.append(health_check.get("response_time_ms", 0))
                    time.sleep(1)  # Wait between requests
                
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    max_response_time = max(response_times)
                    
                    result["details"]["api_performance"] = {
                        "average_response_time_ms": avg_response_time,
                        "max_response_time_ms": max_response_time,
                        "samples": len(response_times)
                    }
                    
                    # Check performance thresholds
                    if avg_response_time > 2000:  # 2 seconds
                        result["status"] = "FAIL"
                        result["errors"].append(f"Average API response time too high: {avg_response_time}ms")
                    
                    if max_response_time > 5000:  # 5 seconds
                        result["status"] = "FAIL"
                        result["errors"].append(f"Max API response time too high: {max_response_time}ms")
            
            # Check Lambda cold start performance
            lambda_functions = [f"tutor-auth-{self.environment}"]  # Test one function
            
            for function_name in lambda_functions:
                try:
                    # Invoke function to measure performance
                    start_time = time.time()
                    response = self.lambda_client.invoke(
                        FunctionName=function_name,
                        InvocationType='RequestResponse',
                        Payload=json.dumps({"test": True})
                    )
                    end_time = time.time()
                    
                    invocation_time = (end_time - start_time) * 1000  # Convert to ms
                    
                    result["details"][f"lambda_{function_name}_performance"] = {
                        "invocation_time_ms": invocation_time,
                        "status_code": response['StatusCode']
                    }
                    
                    # Check Lambda performance thresholds
                    if invocation_time > 10000:  # 10 seconds
                        result["status"] = "FAIL"
                        result["errors"].append(f"Lambda {function_name} invocation too slow: {invocation_time}ms")
                
                except Exception as e:
                    result["errors"].append(f"Lambda performance test failed for {function_name}: {str(e)}")
        
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Performance validation failed: {str(e)}")
        
        return result
    
    def validate_monitoring(self) -> Dict[str, Any]:
        """Validate monitoring and alerting configuration"""
        print("📊 Validating monitoring...")
        
        result = {
            "status": "PASS",
            "details": {},
            "errors": []
        }
        
        try:
            # Check CloudWatch alarms
            alarms = self.cloudwatch.describe_alarms(
                AlarmNamePrefix=f"tutor-"
            )
            
            environment_alarms = [
                alarm for alarm in alarms['MetricAlarms']
                if self.environment in alarm['AlarmName']
            ]
            
            result["details"]["alarm_count"] = len(environment_alarms)
            result["details"]["alarms"] = [
                {
                    "name": alarm['AlarmName'],
                    "state": alarm['StateValue'],
                    "metric": f"{alarm['Namespace']}/{alarm['MetricName']}"
                }
                for alarm in environment_alarms
            ]
            
            # Check for critical alarms
            critical_alarms = [
                f"tutor-api-5xx-errors-{self.environment}",
                f"lambda-tutor-auth-errors-{self.environment}"
            ]
            
            existing_alarm_names = [alarm['AlarmName'] for alarm in environment_alarms]
            missing_critical_alarms = [
                alarm for alarm in critical_alarms
                if alarm not in existing_alarm_names
            ]
            
            if missing_critical_alarms:
                result["status"] = "FAIL"
                result["errors"].append(f"Missing critical alarms: {', '.join(missing_critical_alarms)}")
            
            # Check dashboard exists
            try:
                dashboards = self.cloudwatch.list_dashboards(
                    DashboardNamePrefix=f"TutorSystem-{self.environment}"
                )
                
                if dashboards['DashboardEntries']:
                    result["details"]["dashboard"] = "EXISTS"
                else:
                    result["status"] = "FAIL"
                    result["errors"].append("CloudWatch dashboard not found")
            
            except Exception as e:
                result["errors"].append(f"Dashboard validation failed: {str(e)}")
        
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Monitoring validation failed: {str(e)}")
        
        return result
    
    def validate_integration(self) -> Dict[str, Any]:
        """Validate end-to-end integration"""
        print("🔗 Validating integration...")
        
        result = {
            "status": "PASS",
            "details": {},
            "errors": []
        }
        
        try:
            # Test database connectivity through Lambda
            db_migration_function = f"tutor-db-migrate-{self.environment}"
            
            try:
                response = self.lambda_client.invoke(
                    FunctionName=db_migration_function,
                    InvocationType='RequestResponse',
                    Payload=json.dumps({"test_connection": True})
                )
                
                if response['StatusCode'] == 200:
                    result["details"]["database_connectivity"] = "SUCCESS"
                else:
                    result["status"] = "FAIL"
                    result["errors"].append("Database connectivity test failed")
            
            except Exception as e:
                result["errors"].append(f"Database connectivity test failed: {str(e)}")
            
            # Test Cognito integration
            user_pool_id = self._get_stack_output("TutorSystemStack", "UserPoolId")
            if user_pool_id:
                try:
                    # Try to list users (should work even if empty)
                    self.cognito.list_users(UserPoolId=user_pool_id, Limit=1)
                    result["details"]["cognito_integration"] = "SUCCESS"
                except Exception as e:
                    result["status"] = "FAIL"
                    result["errors"].append(f"Cognito integration test failed: {str(e)}")
            
            # Test S3 integration (frontend bucket)
            frontend_bucket = self._get_stack_output("FrontendStack", "FrontendBucketName")
            if frontend_bucket:
                try:
                    self.s3.head_bucket(Bucket=frontend_bucket)
                    result["details"]["s3_integration"] = "SUCCESS"
                except Exception as e:
                    result["status"] = "FAIL"
                    result["errors"].append(f"S3 integration test failed: {str(e)}")
        
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Integration validation failed: {str(e)}")
        
        return result
    
    def _get_stack_output(self, stack_prefix: str, output_key: str) -> Optional[str]:
        """Get a specific output value from a CloudFormation stack"""
        try:
            stack_name = f"{stack_prefix}-{self.environment}"
            response = self.cloudformation.describe_stacks(StackName=stack_name)
            
            outputs = response['Stacks'][0].get('Outputs', [])
            for output in outputs:
                if output['OutputKey'] == output_key:
                    return output['OutputValue']
            
            return None
            
        except Exception:
            return None
    
    def test_rollback_procedures(self) -> Dict[str, Any]:
        """Test rollback procedures and disaster recovery"""
        print("🔄 Testing rollback procedures...")
        
        result = {
            "status": "PASS",
            "details": {},
            "errors": []
        }
        
        try:
            # This is a dry-run test - we don't actually perform rollbacks
            # but validate that rollback mechanisms are in place
            
            # Check if stacks have rollback configuration
            for stack_name in self.stack_names:
                try:
                    response = self.cloudformation.describe_stacks(StackName=stack_name)
                    stack = response['Stacks'][0]
                    
                    # Check if stack has rollback configuration
                    rollback_config = stack.get('RollbackConfiguration', {})
                    result["details"][f"{stack_name}_rollback_config"] = {
                        "monitoring_time_minutes": rollback_config.get('RollbackTriggers', []),
                        "has_triggers": len(rollback_config.get('RollbackTriggers', [])) > 0
                    }
                    
                except Exception as e:
                    result["errors"].append(f"Rollback validation failed for {stack_name}: {str(e)}")
            
            # Check if database has backup configuration
            try:
                clusters = self.rds.describe_db_clusters()
                for cluster in clusters['DBClusters']:
                    if self.environment in cluster['DBClusterIdentifier']:
                        backup_retention = cluster.get('BackupRetentionPeriod', 0)
                        result["details"]["database_backup"] = {
                            "retention_days": backup_retention,
                            "automated_backups": backup_retention > 0
                        }
                        
                        if backup_retention == 0:
                            result["status"] = "FAIL"
                            result["errors"].append("Database automated backups not enabled")
                        
                        break
            
            except Exception as e:
                result["errors"].append(f"Database backup validation failed: {str(e)}")
            
            # Check Lambda versioning
            lambda_functions = [f"tutor-auth-{self.environment}"]
            
            for function_name in lambda_functions:
                try:
                    versions = self.lambda_client.list_versions_by_function(
                        FunctionName=function_name
                    )
                    
                    version_count = len([v for v in versions['Versions'] if v['Version'] != '$LATEST'])
                    result["details"][f"{function_name}_versions"] = {
                        "version_count": version_count,
                        "has_versions": version_count > 0
                    }
                    
                except Exception as e:
                    result["errors"].append(f"Lambda versioning check failed for {function_name}: {str(e)}")
        
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Rollback procedure validation failed: {str(e)}")
        
        return result


@pytest.fixture
def deployment_validator():
    """Fixture for deployment validator"""
    environment = os.getenv("ENVIRONMENT", "development")
    return DeploymentValidator(environment)


class TestDeploymentValidation:
    """Test class for deployment validation"""
    
    def test_infrastructure_provisioning(self, deployment_validator):
        """Test that all infrastructure is properly provisioned"""
        result = deployment_validator.validate_infrastructure()
        
        assert result["status"] == "PASS", f"Infrastructure validation failed: {result['errors']}"
        assert len(result["errors"]) == 0, f"Infrastructure errors found: {result['errors']}"
    
    def test_service_health_checks(self, deployment_validator):
        """Test that all services are healthy and responding"""
        result = deployment_validator.validate_service_health()
        
        assert result["status"] == "PASS", f"Service health validation failed: {result['errors']}"
        
        # Check specific health indicators
        assert "health_endpoint" in result["details"]
        assert result["details"]["health_endpoint"]["success"] == True
    
    def test_security_configuration(self, deployment_validator):
        """Test security configurations are properly set"""
        result = deployment_validator.validate_security_configuration()
        
        assert result["status"] == "PASS", f"Security validation failed: {result['errors']}"
        
        # Check HTTPS enforcement
        assert result["details"].get("https_enforcement") == "ENABLED"
    
    def test_performance_requirements(self, deployment_validator):
        """Test that performance requirements are met"""
        result = deployment_validator.validate_performance()
        
        assert result["status"] == "PASS", f"Performance validation failed: {result['errors']}"
        
        # Check API performance
        if "api_performance" in result["details"]:
            api_perf = result["details"]["api_performance"]
            assert api_perf["average_response_time_ms"] < 2000, "API response time too high"
    
    def test_monitoring_configuration(self, deployment_validator):
        """Test monitoring and alerting configuration"""
        result = deployment_validator.validate_monitoring()
        
        assert result["status"] == "PASS", f"Monitoring validation failed: {result['errors']}"
        
        # Check that alarms exist
        assert result["details"]["alarm_count"] > 0, "No CloudWatch alarms found"
    
    def test_integration_functionality(self, deployment_validator):
        """Test end-to-end integration functionality"""
        result = deployment_validator.validate_integration()
        
        assert result["status"] == "PASS", f"Integration validation failed: {result['errors']}"
    
    def test_rollback_procedures(self, deployment_validator):
        """Test rollback and disaster recovery procedures"""
        result = deployment_validator.test_rollback_procedures()
        
        assert result["status"] == "PASS", f"Rollback validation failed: {result['errors']}"
    
    def test_complete_deployment_validation(self, deployment_validator):
        """Run complete deployment validation suite"""
        result = deployment_validator.validate_all()
        
        # Print detailed results for debugging
        print(json.dumps(result, indent=2, default=str))
        
        assert result["overall_status"] == "PASS", f"Overall deployment validation failed"
        
        # Ensure all test categories passed
        for test_name, test_result in result["tests"].items():
            assert test_result["status"] == "PASS", f"Test category {test_name} failed: {test_result['errors']}"


def main():
    """Main function for running deployment validation as a script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate deployment infrastructure")
    parser.add_argument(
        "--environment",
        default=os.getenv("ENVIRONMENT", "development"),
        help="Environment to validate"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region"
    )
    parser.add_argument(
        "--output-file",
        help="Output file for validation results"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = DeploymentValidator(args.environment, args.region)
    results = validator.validate_all()
    
    # Output results
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    else:
        print(json.dumps(results, indent=2, default=str))
    
    # Exit with appropriate code
    if results["overall_status"] == "PASS":
        print(f"\n✅ Deployment validation for {args.environment} PASSED")
        return 0
    else:
        print(f"\n❌ Deployment validation for {args.environment} FAILED")
        return 1


if __name__ == "__main__":
    exit(main())