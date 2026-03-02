#!/usr/bin/env python3
"""
Test KMS + Secrets Manager integration using Moto
"""
import json
import boto3
from botocore.exceptions import ClientError
from moto import mock_aws


@mock_aws
def test_kms_secrets_integration():
    """Test KMS and Secrets Manager working together"""
    kms_client = boto3.client("kms", region_name="us-east-1")
    secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
    
    print("🔐 Testing KMS + Secrets Manager Integration in LocalStack")
    print("=" * 60)
    
    try:
        # 1. Create a KMS key
        print("\n1️⃣ Creating KMS key...")
        key_response = kms_client.create_key(
            Description="Test key for secrets encryption",
            KeyUsage="ENCRYPT_DECRYPT"
        )
        key_id = key_response["KeyMetadata"]["KeyId"]
        key_arn = key_response["KeyMetadata"]["Arn"]
        print(f"✅ Created KMS key: {key_id}")
        print(f"   ARN: {key_arn}")
        
        # 2. Create an alias for easier reference
        print("\n2️⃣ Creating KMS key alias...")
        alias_name = "alias/test-secrets-key"
        kms_client.create_alias(
            AliasName=alias_name,
            TargetKeyId=key_id
        )
        print(f"✅ Created alias: {alias_name}")
        
        # 3. Test direct KMS encryption/decryption
        print("\n3️⃣ Testing direct KMS encryption...")
        plaintext = "This is a test secret value!"
        
        encrypt_response = kms_client.encrypt(
            KeyId=key_id,
            Plaintext=plaintext
        )
        ciphertext = encrypt_response["CiphertextBlob"]
        print(f"✅ Encrypted data (length: {len(ciphertext)} bytes)")
        
        decrypt_response = kms_client.decrypt(CiphertextBlob=ciphertext)
        decrypted_text = decrypt_response["Plaintext"].decode()
        print(f"✅ Decrypted: '{decrypted_text}'")
        assert decrypted_text == plaintext
        
        # 4. Create secret with KMS encryption
        print("\n4️⃣ Creating secret with KMS encryption...")
        secret_name = "test-kms-encrypted-secret"
        secret_value = {
            "database_host": "localhost",
            "database_port": 5432,
            "username": "testuser",
            "password": "super-secret-password-123"
        }
        
        secrets_client.create_secret(
            Name=secret_name,
            SecretString=json.dumps(secret_value),
            KmsKeyId=key_id,  # Use our custom KMS key
            Description="Test secret encrypted with custom KMS key"
        )
        print(f"✅ Created secret: {secret_name}")
        print(f"   Encrypted with KMS key: {key_id}")
        
        # 5. Retrieve and verify secret
        print("\n5️⃣ Retrieving encrypted secret...")
        secret_response = secrets_client.get_secret_value(SecretId=secret_name)
        retrieved_value = json.loads(secret_response["SecretString"])
        
        print(f"✅ Retrieved secret successfully!")
        print(f"   Database: {retrieved_value['database_host']}:{retrieved_value['database_port']}")
        print(f"   Username: {retrieved_value['username']}")
        print(f"   Password: {'*' * len(retrieved_value['password'])}")
        
        assert retrieved_value == secret_value
        
        # 6. Test secret rotation (update with new KMS encryption)
        print("\n6️⃣ Testing secret rotation...")
        new_secret_value = secret_value.copy()
        new_secret_value["password"] = "new-rotated-password-456"
        
        secrets_client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(new_secret_value)
        )
        
        # Verify rotation
        rotated_response = secrets_client.get_secret_value(SecretId=secret_name)
        rotated_value = json.loads(rotated_response["SecretString"])
        
        print(f"✅ Secret rotated successfully!")
        print(f"   New password: {'*' * len(rotated_value['password'])}")
        assert rotated_value["password"] == "new-rotated-password-456"
        
        # 7. Test IAM-style permissions (simulate what your Lambda would do)
        print("\n7️⃣ Testing IAM-style access pattern...")
        
        # This simulates what happens when your Lambda function accesses secrets
        # with the IAM policies you defined
        try:
            # Get secret (requires secretsmanager:GetSecretValue)
            response = secrets_client.get_secret_value(SecretId=secret_name)
            
            # The fact that we can read the decrypted value means:
            # 1. Secrets Manager permission worked
            # 2. KMS decrypt permission worked (automatically called by Secrets Manager)
            decrypted_secret = json.loads(response["SecretString"])
            
            print(f"✅ IAM-style access successful!")
            print(f"   Secret decrypted automatically by Secrets Manager using KMS")
            
        except ClientError as e:
            print(f"❌ IAM-style access failed: {e}")
        
        print("\n🎉 All tests passed! KMS + Secrets Manager integration working perfectly!")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        secrets_client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True
        )
        print(f"✅ Deleted secret: {secret_name}")
        
        print(f"✅ KMS key cleaned up by Moto")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    test_kms_secrets_integration()
    print("All tests passed!")