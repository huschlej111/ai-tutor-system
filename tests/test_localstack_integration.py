"""
Integration tests for LocalStack setup
Tests basic AWS service functionality in LocalStack environment
"""
import json
import os
import pytest
import boto3
from botocore.exceptions import ClientError


@pytest.fixture(scope="session")
def localstack_endpoint():
    """Get LocalStack endpoint URL from environment"""
    return os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")


@pytest.fixture(scope="session")
def aws_credentials():
    """Get AWS credentials for LocalStack"""
    return {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "region_name": "us-east-1"
    }


@pytest.fixture
def s3_client(localstack_endpoint, aws_credentials):
    """Create S3 client for LocalStack"""
    return boto3.client(
        "s3",
        endpoint_url=localstack_endpoint,
        **aws_credentials
    )


@pytest.fixture
def rds_client(localstack_endpoint, aws_credentials):
    """Create RDS client for LocalStack"""
    return boto3.client(
        "rds",
        endpoint_url=localstack_endpoint,
        **aws_credentials
    )


@pytest.fixture
def lambda_client(localstack_endpoint, aws_credentials):
    """Create Lambda client for LocalStack"""
    return boto3.client(
        "lambda",
        endpoint_url=localstack_endpoint,
        **aws_credentials
    )


@pytest.fixture
def secrets_client(localstack_endpoint, aws_credentials):
    """Create Secrets Manager client for LocalStack"""
    return boto3.client(
        "secretsmanager",
        endpoint_url=localstack_endpoint,
        **aws_credentials
    )


class TestLocalStackS3:
    """Test S3 functionality in LocalStack"""
    
    def test_list_buckets(self, s3_client):
        """Test listing S3 buckets"""
        response = s3_client.list_buckets()
        assert "Buckets" in response
        
        # Check for expected buckets created by setup script
        bucket_names = [bucket["Name"] for bucket in response["Buckets"]]
        expected_buckets = [
            "tutor-system-uploads-local",
            "tutor-system-static-local",
            "tutor-system-ml-models-local",
            "tutor-system-backups-local"
        ]
        
        for expected_bucket in expected_buckets:
            assert expected_bucket in bucket_names
    
    def test_bucket_operations(self, s3_client):
        """Test basic S3 bucket operations"""
        bucket_name = "test-bucket-operations"
        
        # Create bucket
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Put object
        test_content = "Hello LocalStack!"
        s3_client.put_object(
            Bucket=bucket_name,
            Key="test-file.txt",
            Body=test_content
        )
        
        # Get object
        response = s3_client.get_object(Bucket=bucket_name, Key="test-file.txt")
        content = response["Body"].read().decode("utf-8")
        assert content == test_content
        
        # List objects
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        assert response["KeyCount"] == 1
        assert response["Contents"][0]["Key"] == "test-file.txt"
        
        # Clean up
        s3_client.delete_object(Bucket=bucket_name, Key="test-file.txt")
        s3_client.delete_bucket(Bucket=bucket_name)


class TestLocalStackRDS:
    """Test RDS functionality in LocalStack"""
    
    def test_list_db_instances(self, rds_client):
        """Test listing RDS instances"""
        response = rds_client.describe_db_instances()
        assert "DBInstances" in response
        
        # Check for expected RDS instance created by setup script
        instance_ids = [db["DBInstanceIdentifier"] for db in response["DBInstances"]]
        assert "tutor-system-db" in instance_ids
    
    def test_rds_instance_details(self, rds_client):
        """Test RDS instance configuration"""
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier="tutor-system-db"
        )
        
        assert len(response["DBInstances"]) == 1
        db_instance = response["DBInstances"][0]
        
        assert db_instance["Engine"] == "postgres"
        assert db_instance["DBName"] == "tutor_system"
        assert db_instance["MasterUsername"] == "tutor_user"


class TestLocalStackLambda:
    """Test Lambda functionality in LocalStack"""
    
    def test_list_functions(self, lambda_client):
        """Test listing Lambda functions"""
        response = lambda_client.list_functions()
        assert "Functions" in response
        
        # Check for expected functions created by setup script
        function_names = [func["FunctionName"] for func in response["Functions"]]
        expected_functions = [
            "tutor-system-auth",
            "tutor-system-quiz",
            "tutor-system-progress",
            "tutor-system-ml-inference"
        ]
        
        for expected_function in expected_functions:
            assert expected_function in function_names
    
    def test_invoke_function(self, lambda_client):
        """Test invoking a Lambda function"""
        function_name = "tutor-system-auth"
        
        # Invoke function
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps({"test": "data"})
        )
        
        assert response["StatusCode"] == 200
        
        # Read response
        payload = json.loads(response["Payload"].read())
        assert "statusCode" in payload
        assert payload["statusCode"] == 200


class TestLocalStackSecretsManager:
    """Test Secrets Manager functionality in LocalStack"""
    
    def test_list_secrets(self, secrets_client):
        """Test listing secrets"""
        response = secrets_client.list_secrets()
        assert "SecretList" in response
        
        # Check for expected secrets created by setup script
        secret_names = [secret["Name"] for secret in response["SecretList"]]
        expected_secrets = [
            "tutor-system/database",
            "tutor-system/jwt",
            "tutor-system/ml-model"
        ]
        
        for expected_secret in expected_secrets:
            assert expected_secret in secret_names
    
    def test_secret_operations(self, secrets_client):
        """Test basic secret operations"""
        secret_name = "test-secret"
        secret_value = {"username": "test", "password": "secret123"}
        
        # Create secret
        secrets_client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value)
        )
        
        # Get secret
        response = secrets_client.get_secret_value(SecretId=secret_name)
        retrieved_value = json.loads(response["SecretString"])
        assert retrieved_value == secret_value
        
        # Update secret
        new_value = {"username": "test", "password": "newsecret456"}
        secrets_client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(new_value)
        )
        
        # Verify update
        response = secrets_client.get_secret_value(SecretId=secret_name)
        retrieved_value = json.loads(response["SecretString"])
        assert retrieved_value == new_value
        
        # Clean up
        secrets_client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True
        )


class TestLocalStackKMS:
    """Test KMS functionality in LocalStack"""
    
    def test_list_keys(self):
        """Test listing KMS keys"""
        kms_client = boto3.client(
            "kms",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1"
        )
        
        response = kms_client.list_keys()
        assert "Keys" in response
    
    def test_key_operations(self):
        """Test basic KMS key operations"""
        kms_client = boto3.client(
            "kms",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1"
        )
        
        # Create key
        response = kms_client.create_key(
            Description="Test key for LocalStack",
            KeyUsage="ENCRYPT_DECRYPT"
        )
        key_id = response["KeyMetadata"]["KeyId"]
        
        # Test encryption/decryption
        plaintext = "Hello LocalStack KMS!"
        
        # Encrypt
        encrypt_response = kms_client.encrypt(
            KeyId=key_id,
            Plaintext=plaintext
        )
        ciphertext = encrypt_response["CiphertextBlob"]
        
        # Decrypt
        decrypt_response = kms_client.decrypt(CiphertextBlob=ciphertext)
        decrypted_text = decrypt_response["Plaintext"].decode()
        
        assert decrypted_text == plaintext
        
        # Clean up
        kms_client.schedule_key_deletion(KeyId=key_id, PendingWindowInDays=7)
    
    def test_kms_secrets_integration(self):
        """Test KMS + Secrets Manager integration"""
        kms_client = boto3.client(
            "kms",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1"
        )
        
        secrets_client = boto3.client(
            "secretsmanager",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1"
        )
        
        # Create KMS key
        key_response = kms_client.create_key(
            Description="Test key for secrets encryption"
        )
        key_id = key_response["KeyMetadata"]["KeyId"]
        
        # Create secret with KMS key
        secret_name = "test-kms-secret"
        secret_value = {"database": "test", "password": "encrypted123"}
        
        secrets_client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value),
            KmsKeyId=key_id
        )
        
        # Retrieve secret (should be decrypted automatically)
        response = secrets_client.get_secret_value(SecretId=secret_name)
        retrieved_value = json.loads(response["SecretString"])
        assert retrieved_value == secret_value
        
        # Clean up
        secrets_client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True
        )
        kms_client.schedule_key_deletion(KeyId=key_id, PendingWindowInDays=7)


class TestLocalStackSecretsManager:
    """Test Secrets Manager functionality in LocalStack"""
    
    def test_list_secrets(self, secrets_client):
        """Test listing secrets"""
        response = secrets_client.list_secrets()
        assert "SecretList" in response
        
        # Check for expected secrets created by setup script
        secret_names = [secret["Name"] for secret in response["SecretList"]]
        expected_secrets = [
            "tutor-system/database",
            "tutor-system/jwt",
            "tutor-system/ml-model"
        ]
        
        for expected_secret in expected_secrets:
            assert expected_secret in secret_names
    
    def test_secret_operations(self, secrets_client):
        """Test basic secret operations"""
        secret_name = "test-secret"
        secret_value = {"username": "test", "password": "secret123"}
        
        # Create secret
        secrets_client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value)
        )
        
        # Get secret
        response = secrets_client.get_secret_value(SecretId=secret_name)
        retrieved_value = json.loads(response["SecretString"])
        assert retrieved_value == secret_value
        
        # Update secret
        new_value = {"username": "test", "password": "newsecret456"}
        secrets_client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(new_value)
        )
        
        # Verify update
        response = secrets_client.get_secret_value(SecretId=secret_name)
        retrieved_value = json.loads(response["SecretString"])
        assert retrieved_value == new_value
        
        # Clean up
        secrets_client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True
        )


@pytest.mark.integration
class TestLocalStackIntegration:
    """Integration tests for LocalStack environment"""
    
    def test_localstack_health(self, localstack_endpoint):
        """Test LocalStack health endpoint"""
        import requests
        
        response = requests.get(f"{localstack_endpoint}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "services" in health_data
        
        # Check that required services are running
        required_services = ["s3", "rds", "lambda", "secretsmanager"]
        for service in required_services:
            assert service in health_data["services"]
    
    def test_environment_variables(self):
        """Test that required environment variables are set"""
        required_vars = [
            "LOCALSTACK_ENDPOINT",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_DEFAULT_REGION"
        ]
        
        for var in required_vars:
            assert os.getenv(var) is not None, f"Environment variable {var} not set"
    
    def test_database_connection(self):
        """Test PostgreSQL database connection"""
        import psycopg2
        
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "tutor_system"),
            "user": os.getenv("DB_USER", "tutor_user"),
            "password": os.getenv("DB_PASSWORD", "tutor_password")
        }
        
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            assert version is not None
            
            # Test that tables exist
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ["users", "domains", "terms", "user_progress", "quiz_sessions"]
            for table in expected_tables:
                assert table in tables, f"Table {table} not found"
            
            cursor.close()
            conn.close()
            
        except psycopg2.Error as e:
            pytest.fail(f"Database connection failed: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])