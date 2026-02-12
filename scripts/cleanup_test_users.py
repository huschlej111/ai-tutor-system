#!/usr/bin/env python3
"""
Cleanup script to remove test users from Cognito and RDS database.
Removes users with email patterns like test*, domaintest*, etc.
"""
import boto3
import json
import sys

# Configuration
USER_POOL_ID = "us-east-1_xapIGvbJE"
DB_PROXY_FUNCTION = "TutorSystemStack-dev-DBProxyFunction9188AB04-FbVKref3emug"
REGION = "us-east-1"

# Test email patterns to match
TEST_PATTERNS = ['test', 'domaintest', 'example.com']

def get_cognito_test_users():
    """Get all test users from Cognito"""
    cognito = boto3.client('cognito-idp', region_name=REGION)
    test_users = []
    
    try:
        paginator = cognito.get_paginator('list_users')
        for page in paginator.paginate(UserPoolId=USER_POOL_ID):
            for user in page['Users']:
                email = None
                for attr in user['Attributes']:
                    if attr['Name'] == 'email':
                        email = attr['Value']
                        break
                
                # Check if email matches test patterns
                if email and any(pattern in email.lower() for pattern in TEST_PATTERNS):
                    test_users.append({
                        'username': user['Username'],
                        'email': email,
                        'sub': user['Attributes'][0]['Value'] if user['Attributes'] else None
                    })
    except Exception as e:
        print(f"Error listing Cognito users: {e}")
    
    return test_users


def delete_cognito_user(username):
    """Delete user from Cognito"""
    cognito = boto3.client('cognito-idp', region_name=REGION)
    try:
        cognito.admin_delete_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        return True
    except Exception as e:
        print(f"  Error deleting Cognito user {username}: {e}")
        return False


def delete_rds_user(cognito_sub):
    """Delete user from RDS via DB Proxy Lambda"""
    lambda_client = boto3.client('lambda', region_name=REGION)
    
    try:
        # Delete user's data (cascades to domains, terms, progress, etc.)
        payload = {
            'operation': 'execute_query',
            'query': 'DELETE FROM users WHERE cognito_sub = %s',
            'params': [cognito_sub]
        }
        
        response = lambda_client.invoke(
            FunctionName=DB_PROXY_FUNCTION,
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        return result.get('statusCode') == 200
    except Exception as e:
        print(f"  Error deleting RDS user {cognito_sub}: {e}")
        return False


def main():
    print("🔍 Finding test users...")
    test_users = get_cognito_test_users()
    
    if not test_users:
        print("✅ No test users found!")
        return
    
    print(f"\n📋 Found {len(test_users)} test users:")
    for i, user in enumerate(test_users, 1):
        print(f"  {i}. {user['email']} (username: {user['username']})")
    
    # Confirm deletion
    print(f"\n⚠️  This will delete {len(test_users)} users from both Cognito and RDS.")
    confirm = input("Continue? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Cancelled")
        return
    
    print("\n🗑️  Deleting users...")
    success_count = 0
    
    for user in test_users:
        print(f"\n  Deleting {user['email']}...")
        
        # Delete from RDS first (using cognito_sub)
        if user['sub']:
            rds_success = delete_rds_user(user['sub'])
            if rds_success:
                print(f"    ✅ Deleted from RDS")
            else:
                print(f"    ⚠️  Failed to delete from RDS")
        
        # Delete from Cognito
        cognito_success = delete_cognito_user(user['username'])
        if cognito_success:
            print(f"    ✅ Deleted from Cognito")
            success_count += 1
        else:
            print(f"    ⚠️  Failed to delete from Cognito")
    
    print(f"\n✅ Cleanup complete! Deleted {success_count}/{len(test_users)} users")


if __name__ == '__main__':
    main()
