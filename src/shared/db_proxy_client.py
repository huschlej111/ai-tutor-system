"""
Simple database client wrapper for Lambda functions.
Replaces the missing db_proxy_client module with direct database connections.
"""
from shared.database import get_db_connection


class DBProxyClient:
    """Simple wrapper around direct database connections."""
    
    def __init__(self, function_name=None):
        """Initialize client (function_name ignored - using direct connection)."""
        self.function_name = function_name
    
    def execute_query(self, query, params=None, return_dict=False):
        """Execute a query and return all results."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        
        if query.strip().upper().startswith('SELECT'):
            if return_dict:
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                results = cursor.fetchall()
        else:
            conn.commit()
            results = []
        
        cursor.close()
        conn.close()
        return results
    
    def execute_query_one(self, query, params=None, return_dict=False):
        """Execute a query and return one result."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        
        result = cursor.fetchone()
        if result and return_dict:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, result))
        
        cursor.close()
        conn.close()
        return result
