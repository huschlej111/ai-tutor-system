#!/usr/bin/env python3
"""
Property-based test runner with LocalStack environment setup
Ensures proper environment configuration before running tests
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path


def load_env_file(env_file_path):
    """Load environment variables from file"""
    if not Path(env_file_path).exists():
        print(f"❌ Environment file not found: {env_file_path}")
        return False
    
    with open(env_file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    print(f"✅ Loaded environment from {env_file_path}")
    return True


def check_localstack_health(endpoint="http://localhost:4566", timeout=30):
    """Check if LocalStack is running and healthy"""
    print(f"🔍 Checking LocalStack health at {endpoint}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{endpoint}/health", timeout=5)
            if response.status_code == 200:
                print("✅ LocalStack is healthy")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(".", end="", flush=True)
        time.sleep(2)
    
    print(f"\n❌ LocalStack not responding after {timeout} seconds")
    return False


def setup_localstack_resources():
    """Set up LocalStack resources using the setup script"""
    print("🚀 Setting up LocalStack resources...")
    
    try:
        result = subprocess.run([
            sys.executable, "scripts/localstack_setup.py"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ LocalStack resources set up successfully")
            return True
        else:
            print(f"⚠️ LocalStack setup completed with warnings:")
            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
            return True  # Continue anyway - resources might already exist
            
    except subprocess.TimeoutExpired:
        print("❌ LocalStack setup timed out")
        return False
    except Exception as e:
        print(f"❌ LocalStack setup failed: {e}")
        return False


def check_database_connection():
    """Check if PostgreSQL database is accessible"""
    print("🔍 Checking database connection...")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'tutor_system'),
            user=os.getenv('DB_USER', 'tutor_user'),
            password=os.getenv('DB_PASSWORD', 'tutor_password')
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        
        print("✅ Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Make sure PostgreSQL is running and the database is set up")
        print("   Run: make database-setup")
        return False


def run_property_tests(test_pattern=None):
    """Run property-based tests with proper environment setup"""
    print("🧪 Running property-based tests...")
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    
    # Add markers for property-based tests
    cmd.extend(["-m", "localstack"])
    
    # Add specific test pattern if provided
    if test_pattern:
        cmd.extend(["-k", test_pattern])
    
    # Add property-based test specific options
    cmd.extend([
        "--tb=short",  # Shorter traceback format
        "-x",          # Stop on first failure
        "--durations=10"  # Show 10 slowest tests
    ])
    
    try:
        result = subprocess.run(cmd, timeout=600)  # 10 minute timeout
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 10 minutes")
        return False
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run property-based tests with environment setup")
    parser.add_argument("--test", "-t", help="Specific test pattern to run")
    parser.add_argument("--skip-setup", action="store_true", help="Skip LocalStack setup")
    parser.add_argument("--env-file", default=".env.localstack", help="Environment file to load")
    
    args = parser.parse_args()
    
    print("🚀 Property-Based Test Runner")
    print("=" * 50)
    
    # Step 1: Load environment
    if not load_env_file(args.env_file):
        sys.exit(1)
    
    # Step 2: Check LocalStack
    if not check_localstack_health():
        print("💡 Try running: make localstack-start")
        sys.exit(1)
    
    # Step 3: Set up LocalStack resources (unless skipped)
    if not args.skip_setup:
        if not setup_localstack_resources():
            print("⚠️ Continuing with existing LocalStack setup...")
    
    # Step 4: Check database
    if not check_database_connection():
        print("💡 Try running: make database-setup")
        sys.exit(1)
    
    # Step 5: Run tests
    print("\n" + "=" * 50)
    success = run_property_tests(args.test)
    
    if success:
        print("\n✅ All property-based tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some property-based tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()