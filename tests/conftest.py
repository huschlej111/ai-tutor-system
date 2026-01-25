"""
Pytest configuration and fixtures for Know-It-All Tutor System tests
Handles LocalStack setup and environment configuration
"""
import os
import sys
import pytest
import subprocess
import time
import requests
from pathlib import Path

# Set Cognito environment variables BEFORE any imports
# This ensures they're available when auth handler module is imported
os.environ.setdefault('USER_POOL_ID', 'us-east-1_test123456')
os.environ.setdefault('USER_POOL_CLIENT_ID', 'test-client-id-123456')
os.environ.setdefault('AWS_REGION', 'us-east-1')

# Add src directories to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "shared"))
sys.path.insert(0, str(project_root / "src" / "lambda_functions"))
sys.path.insert(0, str(project_root / "src"))


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may be slow)"
    )
    config.addinivalue_line(
        "markers", "localstack: marks tests that require LocalStack"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment with LocalStack configuration"""
    # Load LocalStack environment variables
    env_file = Path(".env.localstack")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Ensure required environment variables are set
    required_env_vars = {
        'AWS_ACCESS_KEY_ID': 'test',
        'AWS_SECRET_ACCESS_KEY': 'test',
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ENDPOINT_URL': 'http://localhost:4566',
        'LOCALSTACK_ENDPOINT': 'http://localhost:4566',
        'ENVIRONMENT': 'local',
        'DB_HOST': 'localhost',
        'DB_PORT': '5432',
        'DB_NAME': 'tutor_system',
        'DB_USER': 'tutor_user',
        'DB_PASSWORD': 'tutor_password',
        'USER_POOL_ID': 'us-east-1_test123456',
        'USER_POOL_CLIENT_ID': 'test-client-id-123456',
        'AWS_REGION': 'us-east-1'
    }
    
    for key, default_value in required_env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value
    
    # Debug: Print environment variables to verify they're set
    print(f"Environment variables set: DB_HOST={os.environ.get('DB_HOST')}, ENVIRONMENT={os.environ.get('ENVIRONMENT')}")


@pytest.fixture(scope="session")
def localstack_endpoint():
    """Get LocalStack endpoint URL"""
    return os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")


@pytest.fixture(scope="session")
def ensure_localstack_running(localstack_endpoint):
    """Ensure LocalStack is running and properly configured"""
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Check if LocalStack is responding
            response = requests.get(f"{localstack_endpoint}/health", timeout=5)
            if response.status_code == 200:
                print(f"\n✅ LocalStack is running at {localstack_endpoint}")
                
                # Ensure LocalStack resources are set up
                setup_result = subprocess.run([
                    "python", "scripts/localstack_setup.py"
                ], capture_output=True, text=True, timeout=60)
                
                if setup_result.returncode == 0:
                    print("✅ LocalStack resources initialized")
                    return True
                else:
                    print(f"⚠️ LocalStack setup warning: {setup_result.stderr}")
                    # Continue anyway - resources might already exist
                    return True
                    
        except (requests.exceptions.RequestException, subprocess.TimeoutExpired):
            if attempt == 0:
                print(f"\n⏳ Waiting for LocalStack at {localstack_endpoint}...")
            print(".", end="", flush=True)
            time.sleep(retry_delay)
    
    # If LocalStack is not running, try to start it
    print(f"\n🚀 Starting LocalStack...")
    try:
        subprocess.run(["make", "localstack-start"], check=True, timeout=30)
        time.sleep(10)  # Give LocalStack time to start
        
        # Try setup again
        subprocess.run(["python", "scripts/localstack_setup.py"], check=True, timeout=60)
        print("✅ LocalStack started and configured")
        return True
        
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        pytest.skip(f"Could not start LocalStack: {e}")


@pytest.fixture(scope="session")
def database_available():
    """Check if PostgreSQL database is available"""
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'tutor_system'),
            user=os.getenv('DB_USER', 'tutor_user'),
            password=os.getenv('DB_PASSWORD', 'tutor_password')
        )
        conn.close()
        print("✅ PostgreSQL database is available")
        return True
        
    except Exception as e:
        pytest.skip(f"PostgreSQL database not available: {e}")


@pytest.fixture(scope="function")
def clean_database():
    """Clean database before each test that needs it"""
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
        
        # Clean up test data (preserve schema)
        cleanup_queries = [
            "DELETE FROM quiz_sessions WHERE user_id LIKE 'test_%'",
            "DELETE FROM progress_records WHERE user_id LIKE 'test_%'",
            "DELETE FROM terms WHERE domain_id IN (SELECT id FROM domains WHERE user_id LIKE 'test_%')",
            "DELETE FROM domains WHERE user_id LIKE 'test_%'",
            "DELETE FROM users WHERE email LIKE 'test_%@%'",
        ]
        
        for query in cleanup_queries:
            try:
                cursor.execute(query)
            except Exception:
                pass  # Ignore errors for non-existent data
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture
def test_environment(setup_test_environment, ensure_localstack_running, database_available):
    """Complete test environment setup"""
    return {
        'localstack_endpoint': os.getenv('LOCALSTACK_ENDPOINT'),
        'database_available': True,
        'environment': 'test'
    }