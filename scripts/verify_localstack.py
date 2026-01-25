#!/usr/bin/env python3
"""
Verification script for LocalStack setup
Checks that LocalStack is properly configured and running
"""
import json
import json
import os
import sys
import time
from typing import Dict, List

import boto3
import requests
from botocore.exceptions import ClientError


def check_docker():
    """Check if Docker is running"""
    try:
        import subprocess
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_localstack_health(endpoint: str = "http://localhost:4566") -> Dict:
    """Check LocalStack health endpoint"""
    try:
        response = requests.get(f"{endpoint}/health", timeout=10)
        if response.status_code == 200:
            # LocalStack 3.x returns empty response, which is OK
            if not response.text.strip():
                return {"status": "ready", "services": {"localstack": "available"}}
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"status": "ready", "services": {"localstack": "available"}}
        else:
            return {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def check_aws_services(endpoint: str = "http://localhost:4566") -> Dict[str, bool]:
    """Check AWS services in LocalStack"""
    results = {}
    
    # Configure boto3 for LocalStack
    session = boto3.Session()
    config = {
        "endpoint_url": endpoint,
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "region_name": "us-east-1"
    }
    
    # Test S3
    try:
        s3 = session.client("s3", **config)
        s3.list_buckets()
        results["s3"] = True
    except Exception:
        results["s3"] = False
    
    # Test Lambda
    try:
        lambda_client = session.client("lambda", **config)
        lambda_client.list_functions()
        results["lambda"] = True
    except Exception:
        results["lambda"] = False
    
    # Test Secrets Manager
    try:
        secrets = session.client("secretsmanager", **config)
        secrets.list_secrets()
        results["secretsmanager"] = True
    except Exception:
        results["secretsmanager"] = False
    
    return results


def check_database_connection() -> bool:
    """Check PostgreSQL database connection"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "tutor_system"),
            user=os.getenv("DB_USER", "tutor_user"),
            password=os.getenv("DB_PASSWORD", "tutor_password")
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        
        return True
    except Exception:
        return False


def check_environment_variables() -> Dict[str, bool]:
    """Check required environment variables"""
    required_vars = [
        "LOCALSTACK_ENDPOINT",
        "AWS_ACCESS_KEY_ID", 
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "DATABASE_URL"
    ]
    
    return {var: os.getenv(var) is not None for var in required_vars}


def print_status(name: str, status: bool, details: str = ""):
    """Print status with colored output"""
    status_symbol = "✅" if status else "❌"
    print(f"{status_symbol} {name}")
    if details:
        print(f"   {details}")


def main():
    """Main verification function"""
    print("🔍 Verifying LocalStack Setup")
    print("=" * 50)
    
    all_good = True
    
    # Check Docker
    print("\n📦 Docker Status:")
    docker_running = check_docker()
    print_status("Docker is running", docker_running)
    if not docker_running:
        all_good = False
        print("   Please start Docker and try again")
    
    # Check environment variables
    print("\n🌍 Environment Variables:")
    env_vars = check_environment_variables()
    for var, status in env_vars.items():
        print_status(f"{var}", status)
        if not status:
            all_good = False
    
    # Check LocalStack health
    print("\n🏥 LocalStack Health:")
    health = check_localstack_health()
    if "error" in health:
        print_status("LocalStack is running", False, health["error"])
        all_good = False
        print("   Try: make localstack-start")
    else:
        print_status("LocalStack is running", True)
        
        # Show available services
        if "services" in health:
            print("   Available services:")
            for service, status in health["services"].items():
                service_status = status in ["available", "running"]
                print(f"     {'✅' if service_status else '❌'} {service}: {status}")
    
    # Check AWS services
    print("\n☁️  AWS Services:")
    if "error" not in health:
        aws_services = check_aws_services()
        for service, status in aws_services.items():
            print_status(f"{service}", status)
            if not status:
                all_good = False
    else:
        print("   Skipping AWS service checks (LocalStack not running)")
        all_good = False
    
    # Check database
    print("\n🗄️  Database:")
    db_status = check_database_connection()
    print_status("PostgreSQL connection", db_status)
    if not db_status:
        all_good = False
        print("   Try: make localstack-start")
    
    # Summary
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 All checks passed! LocalStack is ready for development.")
        print("\nNext steps:")
        print("  - Run tests: make local-test")
        print("  - Deploy CDK: cdklocal deploy")
        print("  - View LocalStack UI: http://localhost:4566/_localstack/health")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("  - Start LocalStack: make local-dev")
        print("  - Check Docker: docker ps")
        print("  - Load environment: source .env.localstack")
        sys.exit(1)


if __name__ == "__main__":
    main()