"""
Client for invoking the Database Proxy Lambda (Lambda B)
Used by Lambda A to execute database operations
"""
import json
import boto3
import os
from typing import Any, List, Dict, Optional, Tuple

# Initialize Lambda client
lambda_client = boto3.client('lambda')


class DBProxyClient:
    """Client for invoking database proxy Lambda"""
    
    def __init__(self, function_name: str = None):
        """
        Initialize DB Proxy Client
        
        Args:
            function_name: Name of the DB proxy Lambda function
                          Defaults to DB_PROXY_FUNCTION_NAME env var
        """
        self.function_name = function_name or os.environ.get('DB_PROXY_FUNCTION_NAME')
        
        if not self.function_name:
            raise ValueError("DB_PROXY_FUNCTION_NAME environment variable not set")
    
    def _invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the DB proxy Lambda
        
        Args:
            payload: Event payload for the Lambda
            
        Returns:
            Response from the Lambda
        """
        response = lambda_client.invoke(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',  # Synchronous
            Payload=json.dumps(payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        # Check for Lambda errors
        if response.get('FunctionError'):
            raise Exception(f"Lambda invocation error: {response_payload}")
        
        # Parse body
        status_code = response_payload.get('statusCode', 500)
        body = json.loads(response_payload.get('body', '{}'))
        
        if status_code != 200:
            raise Exception(f"Database operation failed: {body.get('error', 'Unknown error')}")
        
        return body
    
    def health_check(self) -> bool:
        """
        Check database health
        
        Returns:
            True if database is healthy
        """
        try:
            result = self._invoke({'operation': 'health_check'})
            return result.get('healthy', False)
        except Exception:
            return False
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        return_dict: bool = False
    ) -> List[Any]:
        """
        Execute a query and return all rows
        
        Args:
            query: SQL query
            params: Query parameters (tuple)
            return_dict: Return rows as dicts instead of tuples
            
        Returns:
            List of rows
        """
        payload = {
            'operation': 'execute_query',
            'query': query,
            'return_dict': return_dict
        }
        
        if params:
            payload['params'] = list(params)
        
        result = self._invoke(payload)
        return result.get('result', [])
    
    def execute_query_one(
        self,
        query: str,
        params: Optional[Tuple] = None,
        return_dict: bool = False
    ) -> Optional[Any]:
        """
        Execute a query and return single row
        
        Args:
            query: SQL query
            params: Query parameters (tuple)
            return_dict: Return row as dict instead of tuple
            
        Returns:
            Single row or None
        """
        payload = {
            'operation': 'execute_query_one',
            'query': query,
            'return_dict': return_dict
        }
        
        if params:
            payload['params'] = list(params)
        
        result = self._invoke(payload)
        return result.get('result')
    
    def execute_many(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> int:
        """
        Execute a query multiple times (batch operation)
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
            
        Returns:
            Number of rows affected
        """
        payload = {
            'operation': 'execute_many',
            'query': query,
            'params_list': [list(p) for p in params_list]
        }
        
        result = self._invoke(payload)
        return result.get('row_count', 0)


# Global instance for easy import
db_proxy = None


def get_db_proxy() -> DBProxyClient:
    """Get or create global DB proxy client instance"""
    global db_proxy
    if db_proxy is None:
        db_proxy = DBProxyClient()
    return db_proxy
