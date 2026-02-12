#!/usr/bin/env python3
"""
Apply database schema to RDS via DB Proxy Lambda
"""
import boto3
import json
import sys
from pathlib import Path

# Initialize Lambda client
lambda_client = boto3.client('lambda')

# DB Proxy Lambda function name
DB_PROXY_FUNCTION = 'TutorSystemStack-dev-DBProxyFunction9188AB04-FbVKref3emug'


def read_sql_file(filepath):
    """Read SQL file and return content"""
    with open(filepath, 'r') as f:
        return f.read()


def execute_sql(sql_content):
    """Execute SQL via DB Proxy Lambda"""
    # Remove comments and split properly
    lines = []
    for line in sql_content.split('\n'):
        # Remove SQL comments
        if '--' in line:
            line = line[:line.index('--')]
        line = line.strip()
        if line:
            lines.append(line)
    
    # Join and split on semicolon
    clean_sql = ' '.join(lines)
    statements = [s.strip() for s in clean_sql.split(';') if s.strip() and not s.startswith('--')]
    
    results = []
    for i, statement in enumerate(statements, 1):
        # Skip if it's just whitespace or comment
        if not statement or statement.startswith('--'):
            continue
            
        print(f"\n[{i}/{len(statements)}] Executing statement...")
        preview = statement[:100].replace('\n', ' ')
        print(f"  {preview}..." if len(statement) > 100 else f"  {preview}")
        
        try:
            payload = {
                'operation': 'execute_query',
                'query': statement,
                'return_dict': False
            }
            
            response = lambda_client.invoke(
                FunctionName=DB_PROXY_FUNCTION,
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') == 200:
                body = json.loads(result['body'])
                print(f"  ✅ Success")
                results.append({'statement': i, 'status': 'success', 'result': body})
            else:
                body = json.loads(result.get('body', '{}'))
                error_msg = body.get('error', 'Unknown error')
                print(f"  ❌ Failed: {error_msg}")
                results.append({'statement': i, 'status': 'error', 'error': error_msg})
                # Don't stop on error, continue with next statement
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append({'statement': i, 'status': 'exception', 'error': str(e)})
    
    return results


def main():
    """Main migration function"""
    print("=" * 80)
    print("Database Schema Migration")
    print("=" * 80)
    
    # Read schema file
    schema_file = Path(__file__).parent.parent / 'scripts' / 'sql' / 'schema_v2.sql'
    
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        sys.exit(1)
    
    print(f"\n📄 Reading schema from: {schema_file}")
    sql_content = read_sql_file(schema_file)
    
    print(f"📊 Found {len([s for s in sql_content.split(';') if s.strip()])} SQL statements")
    
    # Confirm before proceeding
    response = input("\n⚠️  Apply schema to production RDS? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled")
        sys.exit(0)
    
    # Execute migration
    print("\n🚀 Starting migration...")
    results = execute_sql(sql_content)
    
    # Summary
    print("\n" + "=" * 80)
    print("Migration Summary")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] in ['error', 'exception'])
    
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {error_count}")
    
    if error_count > 0:
        print("\n⚠️  Some statements failed. Check the output above for details.")
        sys.exit(1)
    else:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)


if __name__ == '__main__':
    main()
