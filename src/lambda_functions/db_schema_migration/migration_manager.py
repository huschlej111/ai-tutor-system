"""
Quiz Schema Migration Manager
Shared migration logic used by both Lambda and standalone script
"""
import os
import logging
from typing import Dict, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3
import json

logger = logging.getLogger(__name__)


class QuizSchemaMigration:
    """
    Manages database schema migration for quiz engine deployment.
    Validates existing schema and adds missing components.
    """
    
    def __init__(self, db_config: Dict[str, str] = None):
        """
        Initialize migration manager with database configuration.
        
        Args:
            db_config: Database connection parameters
                      If None, reads from Secrets Manager or environment
        """
        if db_config is None:
            db_config = self._get_db_config()
        
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        
        logger.info("Quiz Schema Migration initialized")
    
    def _get_db_config(self) -> Dict[str, str]:
        """
        Get database configuration from AWS Secrets Manager or environment.
        
        Priority:
        1. AWS Secrets Manager (production)
        2. Environment variables (LocalStack/development)
        """
        # Check if we should use AWS Secrets Manager
        secret_arn = os.getenv('DB_SECRET_ARN')
        
        if secret_arn:
            logger.info(f"Using AWS Secrets Manager: {secret_arn}")
            try:
                # Get credentials from Secrets Manager
                session = boto3.session.Session()
                client = session.client(
                    service_name='secretsmanager',
                    region_name=os.getenv('AWS_REGION', 'us-east-1'),
                    endpoint_url=os.getenv('AWS_ENDPOINT_URL')  # For LocalStack
                )
                
                response = client.get_secret_value(SecretId=secret_arn)
                secret = json.loads(response['SecretString'])
                
                return {
                    'host': secret.get('host', 'localhost'),
                    'port': int(secret.get('port', 5432)),
                    'database': secret.get('dbname', 'tutor_system'),
                    'user': secret.get('username', 'tutor_user'),
                    'password': secret.get('password')
                }
            except Exception as e:
                logger.warning(f"Failed to get credentials from Secrets Manager: {e}")
                logger.info("Falling back to environment variables")
        
        # Fallback to environment variables (LocalStack or local development)
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', os.getenv('RDS_DATABASE', 'tutor_system')),
            'user': os.getenv('DB_USER', os.getenv('RDS_USERNAME', 'tutor_user')),
            'password': os.getenv('DB_PASSWORD', os.getenv('RDS_PASSWORD', 'tutor_password'))
        }
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info(f"Connected to database: {self.db_config['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def validate_schema(self) -> Dict[str, bool]:
        """
        Validate that required tables and indexes exist.
        
        Returns:
            Dictionary with validation results for each component
        """
        logger.info("Starting schema validation...")
        validation_results = {}
        
        try:
            # Check quiz_sessions table
            validation_results['quiz_sessions_table'] = self._check_table_exists('quiz_sessions')
            if validation_results['quiz_sessions_table']:
                validation_results['quiz_sessions_schema'] = self._validate_quiz_sessions_schema()
            else:
                validation_results['quiz_sessions_schema'] = False
            
            # Check progress_records table
            validation_results['progress_records_table'] = self._check_table_exists('progress_records')
            if validation_results['progress_records_table']:
                validation_results['progress_records_schema'] = self._validate_progress_records_schema()
            else:
                validation_results['progress_records_schema'] = False
            
            # Check tree_nodes indexes
            required_indexes = [
                'idx_tree_nodes_parent',
                'idx_tree_nodes_type',
                'idx_tree_nodes_user'
            ]
            for index_name in required_indexes:
                validation_results[index_name] = self._check_index_exists(index_name)
            
            # Check quiz-specific indexes
            quiz_indexes = [
                'idx_quiz_sessions_user',
                'idx_quiz_sessions_domain',
                'idx_quiz_sessions_status',
                'idx_progress_user_term',
                'idx_progress_session'
            ]
            for index_name in quiz_indexes:
                validation_results[index_name] = self._check_index_exists(index_name)
            
            # Summary
            all_valid = all(validation_results.values())
            logger.info(f"Schema validation complete. All valid: {all_valid}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            raise
    
    def _check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table_name,))
        exists = self.cursor.fetchone()['exists']
        logger.info(f"Table '{table_name}': {'EXISTS' if exists else 'MISSING'}")
        return exists
    
    def _check_index_exists(self, index_name: str) -> bool:
        """Check if an index exists"""
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE schemaname = 'public'
                AND indexname = %s
            )
        """, (index_name,))
        exists = self.cursor.fetchone()['exists']
        logger.info(f"Index '{index_name}': {'EXISTS' if exists else 'MISSING'}")
        return exists
    
    def _validate_quiz_sessions_schema(self) -> bool:
        """Validate quiz_sessions table has required columns"""
        required_columns = [
            'id', 'user_id', 'domain_id', 'status', 'current_term_index',
            'total_terms', 'started_at', 'paused_at', 'completed_at', 'updated_at'
        ]
        
        self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'quiz_sessions'
        """)
        existing_columns = [row['column_name'] for row in self.cursor.fetchall()]
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.warning(f"quiz_sessions missing columns: {missing_columns}")
            return False
        
        logger.info("quiz_sessions schema: VALID")
        return True
    
    def _validate_progress_records_schema(self) -> bool:
        """Validate progress_records table has required columns"""
        required_columns = [
            'id', 'user_id', 'term_id', 'session_id', 'student_answer',
            'correct_answer', 'is_correct', 'similarity_score', 
            'attempt_number', 'created_at'
        ]
        
        self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'progress_records'
        """)
        existing_columns = [row['column_name'] for row in self.cursor.fetchall()]
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.warning(f"progress_records missing columns: {missing_columns}")
            return False
        
        logger.info("progress_records schema: VALID")
        return True
    
    def apply_migration(self) -> Dict[str, any]:
        """
        Apply database migration to create missing tables and indexes.
        
        Returns:
            Dictionary with migration results
        """
        logger.info("Starting database migration...")
        results = {
            'tables_created': [],
            'indexes_created': [],
            'errors': []
        }
        
        try:
            # Start transaction
            self.conn.autocommit = False
            
            # Create quiz_sessions table if missing
            if not self._check_table_exists('quiz_sessions'):
                self._create_quiz_sessions_table()
                results['tables_created'].append('quiz_sessions')
            
            # Create progress_records table if missing
            if not self._check_table_exists('progress_records'):
                self._create_progress_records_table()
                results['tables_created'].append('progress_records')
            
            # Create indexes
            indexes_to_create = [
                ('idx_tree_nodes_parent', 'tree_nodes', 'parent_id'),
                ('idx_tree_nodes_type', 'tree_nodes', 'node_type'),
                ('idx_tree_nodes_user', 'tree_nodes', 'user_id'),
                ('idx_quiz_sessions_user', 'quiz_sessions', 'user_id'),
                ('idx_quiz_sessions_domain', 'quiz_sessions', 'domain_id'),
                ('idx_quiz_sessions_status', 'quiz_sessions', 'status'),
                ('idx_progress_user_term', 'progress_records', '(user_id, term_id)'),
                ('idx_progress_session', 'progress_records', 'session_id')
            ]
            
            for index_name, table_name, columns in indexes_to_create:
                if not self._check_index_exists(index_name):
                    self._create_index(index_name, table_name, columns)
                    results['indexes_created'].append(index_name)
            
            # Commit transaction
            self.conn.commit()
            logger.info("Migration completed successfully")
            
        except Exception as e:
            # Rollback on error
            self.conn.rollback()
            logger.error(f"Migration failed: {e}")
            results['errors'].append(str(e))
            raise
        finally:
            self.conn.autocommit = True
        
        return results
    
    def _create_quiz_sessions_table(self):
        """Create quiz_sessions table"""
        logger.info("Creating quiz_sessions table...")
        self.cursor.execute("""
            CREATE TABLE quiz_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                domain_id UUID NOT NULL REFERENCES tree_nodes(id) ON DELETE CASCADE,
                status VARCHAR(20) DEFAULT 'active' 
                    CHECK (status IN ('active', 'paused', 'completed')),
                current_term_index INTEGER DEFAULT 0,
                total_terms INTEGER NOT NULL,
                started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                paused_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("quiz_sessions table created")
    
    def _create_progress_records_table(self):
        """Create progress_records table"""
        logger.info("Creating progress_records table...")
        self.cursor.execute("""
            CREATE TABLE progress_records (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                term_id UUID NOT NULL REFERENCES tree_nodes(id) ON DELETE CASCADE,
                session_id UUID REFERENCES quiz_sessions(id) ON DELETE SET NULL,
                student_answer TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                similarity_score DECIMAL(3,2) CHECK (similarity_score BETWEEN 0.0 AND 1.0),
                attempt_number INTEGER DEFAULT 1,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("progress_records table created")
    
    def _create_index(self, index_name: str, table_name: str, columns: str):
        """Create an index"""
        logger.info(f"Creating index {index_name}...")
        self.cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {index_name} 
            ON {table_name} {columns if columns.startswith('(') else f'({columns})'}
        """)
        logger.info(f"Index {index_name} created")
    
    def verify_db_proxy_permissions(self) -> bool:
        """
        Verify DB Proxy Lambda has permissions for quiz tables.
        
        This checks if the database user can perform required operations
        on quiz_sessions and progress_records tables.
        """
        logger.info("Verifying DB Proxy permissions...")
        
        try:
            # Test SELECT permission on quiz_sessions
            self.cursor.execute("SELECT COUNT(*) FROM quiz_sessions")
            
            # Test INSERT permission on quiz_sessions
            self.cursor.execute("""
                SELECT has_table_privilege(current_user, 'quiz_sessions', 'INSERT')
            """)
            can_insert_sessions = self.cursor.fetchone()[0]
            
            # Test SELECT permission on progress_records
            self.cursor.execute("SELECT COUNT(*) FROM progress_records")
            
            # Test INSERT permission on progress_records
            self.cursor.execute("""
                SELECT has_table_privilege(current_user, 'progress_records', 'INSERT')
            """)
            can_insert_progress = self.cursor.fetchone()[0]
            
            if can_insert_sessions and can_insert_progress:
                logger.info("DB Proxy permissions: VALID")
                return True
            else:
                logger.error("DB Proxy missing INSERT permissions")
                return False
                
        except Exception as e:
            logger.error(f"Permission verification failed: {e}")
            return False
