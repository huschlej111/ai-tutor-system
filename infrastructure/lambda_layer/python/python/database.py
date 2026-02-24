"""
Database connection pooling and management for Aurora Serverless PostgreSQL
Uses AWS Secrets Manager + KMS for secure credential management
"""
import os
import json
import boto3
import psycopg
from psycopg_pool import ConnectionPool
from typing import Optional, Dict, Any
from contextlib import contextmanager
import sys

# Add shared directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from secrets_client import get_database_credentials
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections with connection pooling for Lambda functions"""
    
    def __init__(self):
        self.connection_pool: Optional[ConnectionPool] = None
        self.db_config: Optional[Dict[str, str]] = None
        
    def _get_db_config(self) -> Dict[str, str]:
        """Get database configuration from Secrets Manager (KMS encrypted) or LocalStack RDS"""
        if self.db_config is None:
            try:
                # Check if running in LocalStack environment
                is_localstack = os.environ.get('LOCALSTACK_ENDPOINT') is not None
                
                if is_localstack:
                    logger.info("Running in LocalStack environment, using RDS emulation")
                    
                    # Try to get credentials from Secrets Manager first (LocalStack RDS pattern)
                    try:
                        credentials = get_database_credentials()
                        # For LocalStack bridge strategy: use real PostgreSQL container, not LocalStack RDS endpoint
                        self.db_config = {
                            'host': 'localhost',  # Real PostgreSQL container
                            'port': '5432',       # Standard PostgreSQL port
                            'database': credentials.get('dbname', 'tutor_system'),
                            'user': credentials.get('username', 'tutor_user'),
                            'password': credentials.get('password', 'tutor_password')
                        }
                        logger.info(f"LocalStack bridge config from Secrets Manager: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
                    except Exception as e:
                        logger.warning(f"Failed to get LocalStack credentials from Secrets Manager: {e}")
                        # Fallback to environment variables for LocalStack
                        self.db_config = {
                            'host': 'localhost',
                            'port': '5432',
                            'database': os.environ.get('RDS_DATABASE', 'tutor_system'),
                            'user': os.environ.get('RDS_USERNAME', 'tutor_user'),
                            'password': os.environ.get('RDS_PASSWORD', 'tutor_password')
                        }
                        logger.info(f"LocalStack bridge config from environment: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
                else:
                    # Production: Get credentials from Secrets Manager (automatically KMS decrypted)
                    logger.info("Retrieving database credentials from Secrets Manager")
                    credentials = get_database_credentials()
                    
                    self.db_config = {
                        'host': credentials.get('host', 'localhost'),
                        'port': str(credentials.get('port', 5432)),
                        'database': credentials.get('database', 'tutor_system'),
                        'user': credentials.get('username', 'tutor_user'),
                        'password': credentials.get('password')
                    }
                    
                    logger.info(f"Production database config loaded: {credentials.get('host')}:{credentials.get('port')}/{credentials.get('database')}")
                
            except Exception as e:
                logger.warning(f"Failed to get credentials from Secrets Manager: {e}")
                logger.info("Falling back to environment variables")
                
                # Fallback to environment variables for development
                self.db_config = {
                    'host': os.environ.get('DB_HOST', 'localhost'),
                    'port': os.environ.get('DB_PORT', '5432'),
                    'database': os.environ.get('DB_NAME', 'tutor_system'),
                    'user': os.environ.get('DB_USER', 'tutor_user'),
                    'password': os.environ.get('DB_PASSWORD', 'tutor_password')
                }
                
        return self.db_config
    
    def _create_connection_pool(self):
        """Create connection pool for database connections"""
        if self.connection_pool is None:
            config = self._get_db_config()
            
            try:
                logger.info("Creating database connection pool for LocalStack RDS")
                
                # Build connection string for psycopg3
                conninfo = (
                    f"host={config['host']} "
                    f"port={config['port']} "
                    f"dbname={config['database']} "
                    f"user={config['user']} "
                    f"password={config['password']} "
                    f"connect_timeout=10 "
                    f"application_name=tutor-system-lambda"
                )
                
                # Add RDS-specific options for LocalStack
                if 'options' in config:
                    conninfo += f" options={config['options']}"
                
                self.connection_pool = ConnectionPool(
                    conninfo=conninfo,
                    min_size=1,
                    max_size=5,  # Limit connections for Lambda
                    open=True
                )
                logger.info("Database connection pool created successfully")
                
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool"""
        if self.connection_pool is None:
            self._create_connection_pool()
        
        # Psycopg3 pool.connection() is a context manager
        with self.connection_pool.connection() as connection:
            yield connection
    
    @contextmanager
    def get_cursor(self):
        """Get a database cursor with automatic connection management"""
        with self.get_connection() as connection:
            cursor = connection.cursor()
            try:
                yield cursor
                connection.commit()
            except Exception as e:
                connection.rollback()
                raise
            finally:
                cursor.close()
    
    def test_secrets_manager_connection(self) -> bool:
        """Test if we can retrieve credentials from Secrets Manager"""
        try:
            credentials = get_database_credentials()
            required_keys = ['host', 'port', 'dbname', 'username', 'password']
            
            for key in required_keys:
                if key not in credentials:
                    logger.error(f"Missing required credential key: {key}")
                    return False
            
            logger.info("✅ Secrets Manager credentials test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Secrets Manager credentials test failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


def get_db_connection():
    """Get database connection context manager"""
    return db_manager.get_connection()


def get_db_cursor():
    """Get database cursor context manager"""
    return db_manager.get_cursor()


def execute_query(query: str, params: tuple = None) -> Any:
    """Execute a query and return results"""
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        # Check if query returns rows (SELECT, INSERT/UPDATE/DELETE with RETURNING)
        if cursor.description is not None:
            return cursor.fetchall()
        return cursor.rowcount


def execute_query_one(query: str, params: tuple = None) -> Any:
    """Execute a query and return single result"""
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        # Check if query returns rows (SELECT, INSERT/UPDATE/DELETE with RETURNING)
        if cursor.description is not None:
            return cursor.fetchone()
        return cursor.rowcount


def health_check() -> bool:
    """Check database connectivity"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result[0] == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def test_secrets_integration() -> bool:
    """Test Secrets Manager + KMS integration"""
    return db_manager.test_secrets_manager_connection()