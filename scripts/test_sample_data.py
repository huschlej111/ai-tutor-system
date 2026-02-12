#!/usr/bin/env python3
"""
Test inserting sample data into tree_nodes table
"""
import boto3
import json
from datetime import datetime

# Initialize Lambda client
lambda_client = boto3.client('lambda')

# DB Proxy Lambda function name
DB_PROXY_FUNCTION = 'TutorSystemStack-dev-DBProxyFunction9188AB04-FbVKref3emug'


def query_db(query, return_dict=True):
    """Execute query via DB Proxy Lambda"""
    payload = {
        'operation': 'execute_query',
        'query': query,
        'return_dict': return_dict
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
    print("Sample Data Test")
    print("=" * 80)
    
    # First, create a test user (or use existing)
    print("\n1️⃣  Creating test user...")
    try:
        user_result = query_db("""
            INSERT INTO users (cognito_sub, email, first_name, last_name, is_active)
            VALUES ('test-cognito-sub-123', 'testuser@example.com', 'Test', 'User', true)
            ON CONFLICT (cognito_sub) DO UPDATE SET email = EXCLUDED.email
            RETURNING id, email
        """)
        user_id = user_result[0]['id']
        print(f"   ✅ User created/found: {user_result[0]['email']} (ID: {user_id})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Create a domain
    print("\n2️⃣  Creating domain (Python Programming)...")
    try:
        domain_result = query_db(f"""
            INSERT INTO tree_nodes (user_id, node_type, data, metadata)
            VALUES (
                '{user_id}',
                'domain',
                '{{"name": "Python Programming", "description": "Learn Python from basics to advanced"}}',
                '{{"difficulty": "beginner", "estimated_hours": 40}}'
            )
            RETURNING id, data
        """)
        domain_id = domain_result[0]['id']
        print(f"   ✅ Domain created: {domain_result[0]['data']['name']} (ID: {domain_id})")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Create terms under the domain
    print("\n3️⃣  Creating terms...")
    terms = [
        {
            "term": "Variable",
            "definition": "A named storage location that holds a value",
            "example": "x = 10",
            "tags": ["basics", "syntax"]
        },
        {
            "term": "Function",
            "definition": "A reusable block of code that performs a specific task",
            "example": "def greet(name):\\n    return f'Hello, {name}'",
            "tags": ["basics", "functions"]
        },
        {
            "term": "List",
            "definition": "An ordered, mutable collection of items",
            "example": "my_list = [1, 2, 3, 4, 5]",
            "tags": ["data-structures", "basics"]
        }
    ]
    
    term_ids = []
    for term in terms:
        try:
            # Escape single quotes in JSON
            data_json = json.dumps(term).replace("'", "''")
            term_result = query_db(f"""
                INSERT INTO tree_nodes (user_id, parent_id, node_type, data)
                VALUES (
                    '{user_id}',
                    '{domain_id}',
                    'term',
                    '{data_json}'
                )
                RETURNING id, data
            """)
            term_id = term_result[0]['id']
            term_ids.append(term_id)
            print(f"   ✅ Term created: {term_result[0]['data']['term']} (ID: {term_id})")
        except Exception as e:
            print(f"   ❌ Error creating term '{term['term']}': {e}")
    
    # Query back the domain with its terms
    print("\n4️⃣  Querying domain with terms...")
    try:
        domain_query = query_db(f"""
            SELECT 
                d.id as domain_id,
                d.data as domain_data,
                d.created_at as domain_created,
                COUNT(t.id) as term_count
            FROM tree_nodes d
            LEFT JOIN tree_nodes t ON t.parent_id = d.id AND t.node_type = 'term'
            WHERE d.id = '{domain_id}'
            GROUP BY d.id, d.data, d.created_at
        """)
        
        if domain_query:
            result = domain_query[0]
            print(f"   ✅ Domain: {result['domain_data']['name']}")
            print(f"      Terms: {result['term_count']}")
            print(f"      Created: {result['domain_created']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # List all terms
    print("\n5️⃣  Listing all terms in domain...")
    try:
        terms_query = query_db(f"""
            SELECT id, data, created_at
            FROM tree_nodes
            WHERE parent_id = '{domain_id}' AND node_type = 'term'
            ORDER BY created_at
        """)
        
        for term in terms_query:
            print(f"   📝 {term['data']['term']}: {term['data']['definition'][:50]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("✅ Sample data test complete!")
    print("=" * 80)
    print(f"\nTest data created:")
    print(f"  - User ID: {user_id}")
    print(f"  - Domain ID: {domain_id}")
    print(f"  - Term IDs: {', '.join(term_ids)}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        exit(1)
