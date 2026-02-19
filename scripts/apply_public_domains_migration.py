#!/usr/bin/env python3
"""
Apply public domains migration to RDS database via DB Proxy
"""
import boto3
import json
import sys

def apply_migration():
    """Apply the public domains migration"""
    lambda_client = boto3.client('lambda')
    
    # Read migration SQL
    with open('database/migrations/003_add_public_domains.sql', 'r') as f:
        sql = f.read()
    
    # Split into individual statements
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    
    print(f"Applying {len(statements)} SQL statements...")
    
    # Get DB Proxy function name
    db_proxy_function = 'BackendStack-dev-DBProxyFunction9188AB04-tTKiBiDWe6Ww'
    
    for i, statement in enumerate(statements, 1):
        if not statement:
            continue
            
        print(f"\n[{i}/{len(statements)}] Executing: {statement[:80]}...")
        
        payload = {
            'query': statement,
            'params': []
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=db_proxy_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                print(f"✓ Success")
                if 'result' in result:
                    print(f"  Result: {result['result']}")
            else:
                print(f"✗ Failed: {result}")
                return False
                
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    print("\n✅ Migration completed successfully!")
    return True

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
