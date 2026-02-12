#!/usr/bin/env python3
"""
Verify database schema objects exist
"""
import boto3
import json

# Initialize Lambda client
lambda_client = boto3.client('lambda')

# DB Proxy Lambda function name
DB_PROXY_FUNCTION = 'TutorSystemStack-dev-DBProxyFunction9188AB04-FbVKref3emug'


def query_db(query):
    """Execute query via DB Proxy Lambda"""
    payload = {
        'operation': 'execute_query',
        'query': query,
        'return_dict': True
    }
    
    response = lambda_client.invoke(
        FunctionName=DB_PROXY_FUNCTION,
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    
    if result.get('statusCode') == 200:
        body = json.loads(result['body'])
        return body.get('result', [])
    else:
        body = json.loads(result.get('body', '{}'))
        raise Exception(body.get('error', 'Unknown error'))


def main():
    print("=" * 80)
    print("Database Schema Verification")
    print("=" * 80)
    
    # Check tables
    print("\n📋 Tables:")
    tables = query_db("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    for table in tables:
        print(f"  ✅ {table['table_name']}")
    
    # Check indexes
    print("\n🔍 Indexes:")
    indexes = query_db("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        ORDER BY indexname
    """)
    for idx in indexes:
        print(f"  ✅ {idx['indexname']}")
    
    # Check functions
    print("\n⚙️  Functions:")
    functions = query_db("""
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        ORDER BY routine_name
    """)
    for func in functions:
        print(f"  ✅ {func['routine_name']}")
    
    # Check triggers
    print("\n⚡ Triggers:")
    triggers = query_db("""
        SELECT trigger_name, event_object_table 
        FROM information_schema.triggers 
        WHERE trigger_schema = 'public' 
        ORDER BY trigger_name
    """)
    for trig in triggers:
        print(f"  ✅ {trig['trigger_name']} on {trig['event_object_table']}")
    
    # Check constraints
    print("\n🔒 Check Constraints:")
    constraints = query_db("""
        SELECT conname, conrelid::regclass AS table_name
        FROM pg_constraint 
        WHERE contype = 'c' 
        AND connamespace = 'public'::regnamespace
        ORDER BY conname
    """)
    for con in constraints:
        print(f"  ✅ {con['conname']} on {con['table_name']}")
    
    print("\n" + "=" * 80)
    print("✅ Schema verification complete!")
    print("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
