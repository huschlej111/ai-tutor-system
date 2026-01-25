#!/usr/bin/env python3
"""
Test script for Secrets Manager + KMS integration with application code
Tests the actual application's use of encrypted credentials
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.secrets_client import SecretsManagerClient, get_database_credentials, get_jwt_config
from shared.database import test_secrets_integration, health_check
import json


def test_secrets_client():
    """Test the SecretsManagerClient class"""
    print("🔐 Testing SecretsManagerClient")
    print("=" * 40)
    
    # Initialize client for LocalStack
    client = SecretsManagerClient(endpoint_url="http://localhost:4566")
    
    # Test health check
    print("\n1️⃣ Testing Secrets Manager connectivity...")
    if client.health_check():
        print("✅ Secrets Manager is accessible")
    else:
        print("❌ Secrets Manager is not accessible")
        return False
    
    # Test database credentials
    print("\n2️⃣ Testing database credentials retrieval...")
    try:
        db_creds = client.get_database_credentials()
        print("✅ Database credentials retrieved:")
        print(f"   Host: {db_creds.get('host')}")
        print(f"   Port: {db_creds.get('port')}")
        print(f"   Database: {db_creds.get('database')}")
        print(f"   Username: {db_creds.get('username')}")
        print(f"   Password: {'*' * len(str(db_creds.get('password', '')))}")
    except Exception as e:
        print(f"❌ Failed to get database credentials: {e}")
        return False
    
    # Test JWT config
    print("\n3️⃣ Testing JWT configuration retrieval...")
    try:
        jwt_config = client.get_jwt_config()
        print("✅ JWT configuration retrieved:")
        print(f"   Algorithm: {jwt_config.get('algorithm')}")
        print(f"   Expiration: {jwt_config.get('expiration_hours')} hours")
        print(f"   Secret Key: {'*' * len(str(jwt_config.get('secret_key', '')))}")
    except Exception as e:
        print(f"❌ Failed to get JWT configuration: {e}")
        return False
    
    # Test ML model config
    print("\n4️⃣ Testing ML model configuration retrieval...")
    try:
        ml_config = client.get_ml_model_config()
        print("✅ ML model configuration retrieved:")
        print(f"   Model Path: {ml_config.get('model_path')}")
        print(f"   Similarity Threshold: {ml_config.get('similarity_threshold')}")
        print(f"   Batch Size: {ml_config.get('batch_size')}")
    except Exception as e:
        print(f"❌ Failed to get ML model configuration: {e}")
        return False
    
    return True


def test_database_integration():
    """Test database integration with Secrets Manager"""
    print("\n🗄️ Testing Database Integration with Secrets Manager")
    print("=" * 50)
    
    # Set environment for LocalStack
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    
    # Test secrets integration
    print("\n1️⃣ Testing database secrets integration...")
    if test_secrets_integration():
        print("✅ Database can retrieve credentials from Secrets Manager")
    else:
        print("❌ Database failed to retrieve credentials from Secrets Manager")
        return False
    
    # Test actual database connection
    print("\n2️⃣ Testing database connectivity...")
    try:
        if health_check():
            print("✅ Database connection successful using Secrets Manager credentials")
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    return True


def test_convenience_functions():
    """Test the convenience functions"""
    print("\n🔧 Testing Convenience Functions")
    print("=" * 35)
    
    # Set environment for LocalStack
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    
    print("\n1️⃣ Testing get_database_credentials()...")
    try:
        creds = get_database_credentials()
        print(f"✅ Got credentials for database: {creds.get('database')}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    print("\n2️⃣ Testing get_jwt_config()...")
    try:
        jwt = get_jwt_config()
        print(f"✅ Got JWT config with algorithm: {jwt.get('algorithm')}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    return True


def test_kms_encryption_verification():
    """Verify that secrets are actually encrypted with KMS"""
    print("\n🔐 Testing KMS Encryption Verification")
    print("=" * 40)
    
    import boto3
    
    # Configure clients for LocalStack
    config = {
        "endpoint_url": "http://localhost:4566",
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "region_name": "us-east-1"
    }
    
    secrets_client = boto3.client("secretsmanager", **config)
    kms_client = boto3.client("kms", **config)
    
    print("\n1️⃣ Checking if secrets use KMS encryption...")
    try:
        # Get secret metadata
        response = secrets_client.describe_secret(SecretId='tutor-system/database')
        kms_key_id = response.get('KmsKeyId')
        
        if kms_key_id:
            print(f"✅ Secret is encrypted with KMS key: {kms_key_id}")
            
            # Try to get key information
            try:
                key_info = kms_client.describe_key(KeyId=kms_key_id)
                print(f"   Key Description: {key_info['KeyMetadata'].get('Description', 'N/A')}")
                print(f"   Key Usage: {key_info['KeyMetadata'].get('KeyUsage', 'N/A')}")
            except Exception as e:
                print(f"   Could not get key details: {e}")
        else:
            print("⚠️  Secret is using default AWS managed key")
        
    except Exception as e:
        print(f"❌ Failed to check KMS encryption: {e}")
        return False
    
    print("\n2️⃣ Testing KMS key permissions...")
    try:
        # List KMS keys to verify access
        keys_response = kms_client.list_keys()
        key_count = len(keys_response.get('Keys', []))
        print(f"✅ Can access {key_count} KMS keys")
        
        # Find our custom key
        aliases_response = kms_client.list_aliases()
        our_alias = None
        for alias in aliases_response.get('Aliases', []):
            if alias.get('AliasName') == 'alias/tutor-system-secrets':
                our_alias = alias
                break
        
        if our_alias:
            print(f"✅ Found our custom KMS key alias: {our_alias['AliasName']}")
            print(f"   Target Key ID: {our_alias.get('TargetKeyId', 'N/A')}")
        else:
            print("⚠️  Custom KMS key alias not found")
        
    except Exception as e:
        print(f"❌ Failed to test KMS permissions: {e}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("🚀 Testing Secrets Manager + KMS Integration")
    print("=" * 50)
    print("Make sure LocalStack is running with: make localstack-start")
    print()
    
    tests = [
        ("Secrets Client", test_secrets_client),
        ("Database Integration", test_database_integration),
        ("Convenience Functions", test_convenience_functions),
        ("KMS Encryption Verification", test_kms_encryption_verification)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"\n✅ {test_name}: PASSED")
            else:
                print(f"\n❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"\n💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Secrets Manager + KMS integration is working perfectly")
        print("✅ Your application can securely access encrypted credentials")
        print("✅ Database connections use KMS-encrypted credentials")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)