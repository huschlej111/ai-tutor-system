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
    
    # Get DB Proxy function name
    db_proxy_function = 'BackendStack-dev-DBProxyFunction9188AB04-tTKiBiDWe6Ww'
    
    # Define migration statements
    statements = [
        "ALTER TABLE tree_nodes ADD COLUMN is_public BOOLEAN DEFAULT false NOT NULL",
        "CREATE INDEX idx_tree_nodes_public ON tree_nodes(is_public) WHERE is_public = true",
        "CREATE INDEX idx_tree_nodes_domain_access ON tree_nodes(node_type, user_id, is_public)",
        "UPDATE tree_nodes SET is_public = true WHERE node_type = 'domain' AND user_id IN (SELECT id FROM users WHERE email = 'huschlej@comcast.net')",
        "SELECT node_type, is_public, COUNT(*) as count FROM tree_nodes GROUP BY node_type, is_public ORDER BY node_type, is_public"
    ]
    
    print(f"Applying {len(statements)} SQL statements...")
    
    for i, statement in enumerate(statements, 1):
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
                if 'result' in result and result['result']:
                    print(f"  Result: {result['result'][:200] if isinstance(result['result'], str) else result['result']}")
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
