"""
Unit tests for db_proxy Lambda handler
Tests database proxy operations
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.mark.unit
class TestDbProxyHandler:
    """Test database proxy Lambda handler"""
    
    @patch('lambda_functions.db_proxy.handler.health_check')
    def test_health_check_success(self, mock_health):
        """Test health check operation"""
        from lambda_functions.db_proxy.handler import lambda_handler
        
        mock_health.return_value = True
        
        event = {'operation': 'health_check'}
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['healthy'] is True
    
    @patch('lambda_functions.db_proxy.handler.health_check')
    def test_health_check_failure(self, mock_health):
        """Test health check when database is down"""
        from lambda_functions.db_proxy.handler import lambda_handler
        
        mock_health.return_value = False
        
        event = {'operation': 'health_check'}
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert body['healthy'] is False
    
    @patch('lambda_functions.db_proxy.handler.execute_query')
    def test_execute_query_success(self, mock_execute):
        """Test execute_query operation"""
        from lambda_functions.db_proxy.handler import lambda_handler
        
        mock_execute.return_value = [('user1', 'test@example.com'), ('user2', 'test2@example.com')]
        
        event = {
            'operation': 'execute_query',
            'query': 'SELECT id, email FROM users',
            'params': None
        }
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['result']) == 2
        assert body['row_count'] == 2
    
    @patch('lambda_functions.db_proxy.handler.execute_query')
    def test_execute_query_with_params(self, mock_execute):
        """Test execute_query with parameters"""
        from lambda_functions.db_proxy.handler import lambda_handler
        
        mock_execute.return_value = [('user1', 'test@example.com')]
        
        event = {
            'operation': 'execute_query',
            'query': 'SELECT id, email FROM users WHERE email = %s',
            'params': ['test@example.com']
        }
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        mock_execute.assert_called_once()
    
    @patch('lambda_functions.db_proxy.handler.execute_query_one')
    def test_execute_query_one_success(self, mock_execute):
        """Test execute_query_one operation"""
        from lambda_functions.db_proxy.handler import lambda_handler
        
        mock_execute.return_value = ('user1', 'test@example.com')
        
        event = {
            'operation': 'execute_query_one',
            'query': 'SELECT id, email FROM users WHERE id = %s',
            'params': ['user1']
        }
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['result'] == ['user1', 'test@example.com']
    
    @patch('lambda_functions.db_proxy.handler.execute_query_one')
    def test_execute_query_one_not_found(self, mock_execute):
        """Test execute_query_one when no result"""
        from lambda_functions.db_proxy.handler import lambda_handler
        
        mock_execute.return_value = None
        
        event = {
            'operation': 'execute_query_one',
            'query': 'SELECT id FROM users WHERE id = %s',
            'params': ['nonexistent']
        }
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['result'] is None
    
    def test_missing_operation(self):
        """Test error when operation is missing"""
        from lambda_functions.db_proxy.handler import lambda_handler
        
        event = {}
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_missing_query(self):
        """Test error when query is missing"""
        from lambda_functions.db_proxy.handler import lambda_handler
        
        event = {'operation': 'execute_query'}
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_json_serial_datetime(self):
        """Test JSON serialization of datetime"""
        from lambda_functions.db_proxy.handler import json_serial
        
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = json_serial(dt)
        assert '2024-01-01' in result
    
    def test_json_serial_decimal(self):
        """Test JSON serialization of Decimal"""
        from lambda_functions.db_proxy.handler import json_serial
        
        dec = Decimal('123.45')
        result = json_serial(dec)
        assert result == 123.45
    
    def test_json_serial_uuid(self):
        """Test JSON serialization of UUID"""
        from lambda_functions.db_proxy.handler import json_serial
        
        uid = UUID('12345678-1234-5678-1234-567812345678')
        result = json_serial(uid)
        assert result == '12345678-1234-5678-1234-567812345678'
