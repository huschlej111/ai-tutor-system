#!/usr/bin/env python3
"""
Deployment script for Know-It-All Tutor System
Handles environment-specific deployments with proper sequencing
"""
import argparse
import subprocess
import sys
import json
import os
import time
from typing import Dict, Any, Optional


class TutorSystemDeployer:
    """Handles deployment of the tutor system infrastructure"""
    
    def __init__(self, environment: str, region: str = "us-east-1", account: Optional[str] = None):
        self.environment = environment
        self.region = region
        self.account = account
        self.stack_prefix = f"TutorSystem-{environment}"
        
        # Validate environment
        if environment not in ["development", "production"]:
            raise ValueError("Environment must be 'development' or 'production'")
    
    def deploy_all(self, skip_tests: bool = False) -> bool:
        """Deploy all stacks in the correct order"""
        print(f"🚀 Starting deployment to {self.environment} environment...")
        
        try:
            # Step 1: Run tests (unless skipped)
            if not skip_tests:
                if not self._run_tests():
                    print("❌ Tests failed. Aborting deployment.")
                    return False
            
            # Step 2: Bootstrap CDK (if needed)
            if not self._bootstrap_cdk():
                print("❌ CDK bootstrap failed.")
                return False
            
            # Step 3: Deploy stacks in order
            stacks_to_deploy = [
                f"SecurityMonitoringStack-{self.environment}",
                f"PipelineStack-{self.environment}",
                f"TutorSystemStack-{self.environment}",
                f"FrontendStack-{self.environment}"
            ]
            
            for stack in stacks_to_deploy:
                if not self._deploy_stack(stack):
                    print(f"❌ Failed to deploy {stack}")
                    return False
                
                # Wait between deployments to avoid rate limits
                time.sleep(10)
            
            # Step 4: Run database migrations
            if not self._run_migrations():
                print("❌ Database migrations failed.")
                return False
            
            # Step 5: Deploy frontend
            if not self._deploy_frontend():
                print("❌ Frontend deployment failed.")
                return False
            
            # Step 6: Run post-deployment validation
            if not self._validate_deployment():
                print("❌ Deployment validation failed.")
                return False
            
            print(f"✅ Deployment to {self.environment} completed successfully!")
            self._print_deployment_info()
            return True
            
        except Exception as e:
            print(f"❌ Deployment failed with error: {str(e)}")
            return False
    
    def _run_tests(self) -> bool:
        """Run test suite before deployment"""
        print("🧪 Running test suite...")
        
        try:
            # Run Python tests
            result = subprocess.run([
                "python", "-m", "pytest", "tests/", "-v", 
                "--cov=src", "--cov-report=term-missing"
            ], capture_output=True, text=True, cwd="..")
            
            if result.returncode != 0:
                print("❌ Python tests failed:")
                print(result.stdout)
                print(result.stderr)
                return False
            
            # Run frontend tests
            result = subprocess.run([
                "npm", "test", "--", "--coverage", "--watchAll=false"
            ], capture_output=True, text=True, cwd="../frontend")
            
            if result.returncode != 0:
                print("❌ Frontend tests failed:")
                print(result.stdout)
                print(result.stderr)
                return False
            
            print("✅ All tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Error running tests: {str(e)}")
            return False
    
    def _bootstrap_cdk(self) -> bool:
        """Bootstrap CDK for the target environment"""
        print("🔧 Bootstrapping CDK...")
        
        try:
            cmd = ["cdk", "bootstrap"]
            
            if self.account:
                cmd.extend(["--context", f"account={self.account}"])
            
            cmd.extend([
                "--context", f"environment={self.environment}",
                "--context", f"region={self.region}"
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print("❌ CDK bootstrap failed:")
                print(result.stderr)
                return False
            
            print("✅ CDK bootstrap completed!")
            return True
            
        except Exception as e:
            print(f"❌ Error bootstrapping CDK: {str(e)}")
            return False
    
    def _deploy_stack(self, stack_name: str) -> bool:
        """Deploy a specific CDK stack"""
        print(f"📦 Deploying {stack_name}...")
        
        try:
            cmd = [
                "cdk", "deploy", stack_name,
                "--require-approval", "never",
                "--context", f"environment={self.environment}",
                "--context", f"region={self.region}"
            ]
            
            if self.account:
                cmd.extend(["--context", f"account={self.account}"])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Failed to deploy {stack_name}:")
                print(result.stderr)
                return False
            
            print(f"✅ {stack_name} deployed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error deploying {stack_name}: {str(e)}")
            return False
    
    def _run_migrations(self) -> bool:
        """Run database migrations"""
        print("🗄️ Running database migrations...")
        
        try:
            # Get the migration function name
            function_name = f"tutor-db-migrate-{self.environment}"
            
            # Invoke the migration Lambda function
            result = subprocess.run([
                "aws", "lambda", "invoke",
                "--function-name", function_name,
                "--payload", "{}",
                "/tmp/migration-result.json"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print("❌ Migration invocation failed:")
                print(result.stderr)
                return False
            
            # Check migration result
            try:
                with open("/tmp/migration-result.json", "r") as f:
                    migration_result = json.load(f)
                
                if migration_result.get("statusCode") != 200:
                    print("❌ Database migration failed:")
                    print(json.dumps(migration_result, indent=2))
                    return False
                
            except Exception as e:
                print(f"❌ Error reading migration result: {str(e)}")
                return False
            
            print("✅ Database migrations completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error running migrations: {str(e)}")
            return False
    
    def _deploy_frontend(self) -> bool:
        """Deploy frontend application"""
        print("🌐 Deploying frontend application...")
        
        try:
            # Build frontend
            print("Building frontend...")
            result = subprocess.run([
                "npm", "run", "build"
            ], capture_output=True, text=True, cwd="../frontend")
            
            if result.returncode != 0:
                print("❌ Frontend build failed:")
                print(result.stderr)
                return False
            
            # Get S3 bucket name from CloudFormation outputs
            bucket_name = self._get_stack_output(
                f"FrontendStack-{self.environment}",
                "FrontendBucketName"
            )
            
            if not bucket_name:
                print("❌ Could not get frontend bucket name")
                return False
            
            # Deploy to S3
            print(f"Uploading to S3 bucket: {bucket_name}")
            
            if self.environment == "production":
                # Production deployment with cache optimization
                
                # Upload non-HTML files with long-term caching
                result = subprocess.run([
                    "aws", "s3", "sync", "../frontend/dist/", f"s3://{bucket_name}",
                    "--delete",
                    "--cache-control", "public, max-age=31536000, immutable",
                    "--exclude", "*.html"
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    print("❌ S3 sync (assets) failed:")
                    print(result.stderr)
                    return False
                
                # Upload HTML files with no caching
                result = subprocess.run([
                    "aws", "s3", "sync", "../frontend/dist/", f"s3://{bucket_name}",
                    "--cache-control", "public, max-age=0, must-revalidate",
                    "--include", "*.html"
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    print("❌ S3 sync (HTML) failed:")
                    print(result.stderr)
                    return False
                
                # Invalidate CloudFront cache
                distribution_id = self._get_stack_output(
                    f"FrontendStack-{self.environment}",
                    "CloudFrontDistributionId"
                )
                
                if distribution_id:
                    print("Invalidating CloudFront cache...")
                    result = subprocess.run([
                        "aws", "cloudfront", "create-invalidation",
                        "--distribution-id", distribution_id,
                        "--paths", "/*"
                    ], capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        print("⚠️ CloudFront invalidation failed (non-critical):")
                        print(result.stderr)
            
            else:
                # Development deployment (simple sync)
                result = subprocess.run([
                    "aws", "s3", "sync", "../frontend/dist/", f"s3://{bucket_name}",
                    "--delete"
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    print("❌ S3 sync failed:")
                    print(result.stderr)
                    return False
            
            print("✅ Frontend deployed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error deploying frontend: {str(e)}")
            return False
    
    def _validate_deployment(self) -> bool:
        """Validate the deployment by testing key endpoints"""
        print("🔍 Validating deployment...")
        
        try:
            # Get API Gateway URL
            api_url = self._get_stack_output(
                f"TutorSystemStack-{self.environment}",
                "APIGatewayURL"
            )
            
            if not api_url:
                print("❌ Could not get API Gateway URL")
                return False
            
            # Test health endpoint
            import requests
            
            health_url = f"{api_url}health"
            response = requests.get(health_url, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Health check failed: {response.status_code}")
                return False
            
            # Get frontend URL
            frontend_url = self._get_stack_output(
                f"FrontendStack-{self.environment}",
                "FrontendURL"
            )
            
            if frontend_url:
                # Test frontend accessibility
                response = requests.get(frontend_url, timeout=30)
                
                if response.status_code != 200:
                    print(f"⚠️ Frontend accessibility check failed: {response.status_code}")
                    # Non-critical for deployment success
            
            print("✅ Deployment validation passed!")
            return True
            
        except Exception as e:
            print(f"❌ Error validating deployment: {str(e)}")
            return False
    
    def _get_stack_output(self, stack_name: str, output_key: str) -> Optional[str]:
        """Get a specific output value from a CloudFormation stack"""
        try:
            result = subprocess.run([
                "aws", "cloudformation", "describe-stacks",
                "--stack-name", stack_name,
                "--query", f"Stacks[0].Outputs[?OutputKey=='{output_key}'].OutputValue",
                "--output", "text"
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            
            return None
            
        except Exception:
            return None
    
    def _print_deployment_info(self):
        """Print deployment information and URLs"""
        print("\n📋 Deployment Information:")
        print("=" * 50)
        
        # API Gateway URL
        api_url = self._get_stack_output(
            f"TutorSystemStack-{self.environment}",
            "APIGatewayURL"
        )
        if api_url:
            print(f"API Gateway URL: {api_url}")
        
        # Frontend URL
        frontend_url = self._get_stack_output(
            f"FrontendStack-{self.environment}",
            "FrontendURL"
        )
        if frontend_url:
            print(f"Frontend URL: {frontend_url}")
        
        # Cognito User Pool ID
        user_pool_id = self._get_stack_output(
            f"TutorSystemStack-{self.environment}",
            "UserPoolId"
        )
        if user_pool_id:
            print(f"Cognito User Pool ID: {user_pool_id}")
        
        # Database endpoint
        db_endpoint = self._get_stack_output(
            f"TutorSystemStack-{self.environment}",
            "AuroraEndpoint"
        )
        if db_endpoint:
            print(f"Database Endpoint: {db_endpoint}")
        
        print("=" * 50)


def main():
    """Main deployment script entry point"""
    parser = argparse.ArgumentParser(description="Deploy Know-It-All Tutor System")
    parser.add_argument(
        "environment",
        choices=["development", "production"],
        help="Target environment for deployment"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region for deployment (default: us-east-1)"
    )
    parser.add_argument(
        "--account",
        help="AWS account ID (optional)"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests before deployment"
    )
    
    args = parser.parse_args()
    
    # Change to infrastructure directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../infrastructure")
    
    # Create deployer and run deployment
    deployer = TutorSystemDeployer(
        environment=args.environment,
        region=args.region,
        account=args.account
    )
    
    success = deployer.deploy_all(skip_tests=args.skip_tests)
    
    if success:
        print(f"\n🎉 Deployment to {args.environment} completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Deployment to {args.environment} failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()