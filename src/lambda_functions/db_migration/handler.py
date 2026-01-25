"""
Database Migration Lambda Function
Handles schema migrations with version tracking and rollback capabilities
Requirements: 5.1, 5.4
"""
import json
import os
import logging
import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Import shared modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from database import get_db_connection, get_db_cursor
from response_utils import create_response, handle_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class MigrationManager:
    """Manages database schema migrations with version tracking"""
    
    def __init__(self):
        self.migrations = {
            '1.0.0': {
                'description': 'Initial schema with legacy tables',
                'file': 'init.sql',
                'rollback_file': None
            },
            '2.0.0': {
                'description': 'Tree-based domain-agnostic architecture',
                'file': 'schema_v2.sql',
                'rollback_file': 'rollback_v2.sql'
            }
        }
    
    def get_current_version(self) -> Optional[str]:
        """Get current database schema version"""
        try:
            with get_db_cursor() as cursor:
                # Create migrations table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(20) PRIMARY KEY,
                        description TEXT,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        applied_by VARCHAR(100),
                        rollback_file VARCHAR(255)
                    )
                """)
                
                # Get latest version
                cursor.execute("""
                    SELECT version FROM schema_migrations 
                    ORDER BY applied_at DESC LIMIT 1
                """)
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Failed to get current version: {e}")
            return None
    
    def apply_migration(self, target_version: str, applied_by: str = 'lambda') -> Dict[str, Any]:
        """Apply migration to target version"""
        try:
            current_version = self.get_current_version()
            logger.info(f"Current version: {current_version}, Target: {target_version}")
            
            if current_version == target_version:
                return {
                    'success': True,
                    'message': f'Already at version {target_version}',
                    'current_version': current_version
                }
            
            if target_version not in self.migrations:
                raise ValueError(f"Unknown migration version: {target_version}")
            
            migration = self.migrations[target_version]
            
            # Read migration file
            migration_sql = self._read_migration_file(migration['file'])
            
            # Apply migration in transaction
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Execute migration SQL
                    cursor.execute(migration_sql)
                    
                    # Record migration
                    cursor.execute("""
                        INSERT INTO schema_migrations 
                        (version, description, applied_by, rollback_file)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (version) DO UPDATE SET
                            applied_at = CURRENT_TIMESTAMP,
                            applied_by = EXCLUDED.applied_by
                    """, (
                        target_version,
                        migration['description'],
                        applied_by,
                        migration.get('rollback_file')
                    ))
                    
                    conn.commit()
            
            logger.info(f"Successfully applied migration to version {target_version}")
            return {
                'success': True,
                'message': f'Migration to version {target_version} completed',
                'previous_version': current_version,
                'current_version': target_version
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'current_version': current_version
            }
    
    def rollback_migration(self, target_version: str) -> Dict[str, Any]:
        """Rollback to previous version"""
        try:
            current_version = self.get_current_version()
            
            if not current_version:
                raise ValueError("No current version found")
            
            if current_version == target_version:
                return {
                    'success': True,
                    'message': f'Already at version {target_version}'
                }
            
            # Get rollback file for current version
            current_migration = self.migrations.get(current_version)
            if not current_migration or not current_migration.get('rollback_file'):
                raise ValueError(f"No rollback available for version {current_version}")
            
            # Read rollback file
            rollback_sql = self._read_migration_file(current_migration['rollback_file'])
            
            # Apply rollback in transaction
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Execute rollback SQL
                    cursor.execute(rollback_sql)
                    
                    # Remove migration record
                    cursor.execute("""
                        DELETE FROM schema_migrations WHERE version = %s
                    """, (current_version,))
                    
                    conn.commit()
            
            logger.info(f"Successfully rolled back from version {current_version}")
            return {
                'success': True,
                'message': f'Rollback from version {current_version} completed',
                'previous_version': current_version,
                'current_version': target_version
            }
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_schema(self) -> Dict[str, Any]:
        """Validate current schema integrity"""
        try:
            validation_results = []
            
            with get_db_cursor() as cursor:
                # Check required tables exist
                required_tables = [
                    'users', 'tree_nodes', 'quiz_sessions', 
                    'progress_records', 'batch_uploads'
                ]
                
                for table in required_tables:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = %s
                        )
                    """, (table,))
                    
                    exists = cursor.fetchone()[0]
                    validation_results.append({
                        'table': table,
                        'exists': exists,
                        'status': 'OK' if exists else 'MISSING'
                    })
                
                # Check indexes exist
                required_indexes = [
                    'idx_tree_nodes_parent', 'idx_tree_nodes_user',
                    'idx_tree_nodes_type', 'idx_tree_nodes_data_gin'
                ]
                
                for index in required_indexes:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM pg_indexes 
                            WHERE indexname = %s
                        )
                    """, (index,))
                    
                    exists = cursor.fetchone()[0]
                    validation_results.append({
                        'index': index,
                        'exists': exists,
                        'status': 'OK' if exists else 'MISSING'
                    })
            
            # Check if all validations passed
            all_passed = all(
                result['status'] == 'OK' 
                for result in validation_results
            )
            
            return {
                'success': True,
                'valid': all_passed,
                'results': validation_results
            }
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _read_migration_file(self, filename: str) -> str:
        """Read migration SQL file"""
        # In Lambda, files would be in the deployment package
        # For now, return the schema content directly
        if filename == 'schema_v2.sql':
            return self._get_schema_v2_sql()
        elif filename == 'rollback_v2.sql':
            return self._get_rollback_v2_sql()
        else:
            raise ValueError(f"Unknown migration file: {filename}")
    
    def _get_schema_v2_sql(self) -> str:
        """Get schema v2 SQL content"""
        return """
        -- Database Schema V2: Tree-based Domain-Agnostic Architecture
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            is_active BOOLEAN DEFAULT true,
            is_verified BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP WITH TIME ZONE
        );
        
        -- Tree nodes table
        CREATE TABLE IF NOT EXISTS tree_nodes (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            parent_id UUID REFERENCES tree_nodes(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) NOT NULL,
            node_type VARCHAR(50) NOT NULL CHECK (node_type IN ('domain', 'category', 'term')),
            data JSONB NOT NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Quiz sessions table
        CREATE TABLE IF NOT EXISTS quiz_sessions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES users(id) NOT NULL,
            domain_id UUID REFERENCES tree_nodes(id) NOT NULL,
            status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
            current_term_index INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP WITH TIME ZONE,
            paused_at TIMESTAMP WITH TIME ZONE,
            session_data JSONB DEFAULT '{}'
        );
        
        -- Progress records table
        CREATE TABLE IF NOT EXISTS progress_records (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES users(id) NOT NULL,
            term_id UUID REFERENCES tree_nodes(id) NOT NULL,
            session_id UUID REFERENCES quiz_sessions(id),
            student_answer TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            similarity_score DECIMAL(3,2) CHECK (similarity_score BETWEEN 0.0 AND 1.0),
            attempt_number INTEGER DEFAULT 1,
            feedback TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Batch uploads table
        CREATE TABLE IF NOT EXISTS batch_uploads (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            admin_id UUID REFERENCES users(id) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            subject_count INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
            uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            metadata JSONB DEFAULT '{}'
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_tree_nodes_parent ON tree_nodes(parent_id);
        CREATE INDEX IF NOT EXISTS idx_tree_nodes_user ON tree_nodes(user_id);
        CREATE INDEX IF NOT EXISTS idx_tree_nodes_type ON tree_nodes(node_type);
        CREATE INDEX IF NOT EXISTS idx_tree_nodes_data_gin ON tree_nodes USING GIN (data);
        CREATE INDEX IF NOT EXISTS idx_progress_user_term ON progress_records(user_id, term_id);
        CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_batch_uploads_admin ON batch_uploads(admin_id);
        """
    
    def _get_rollback_v2_sql(self) -> str:
        """Get rollback SQL for v2"""
        return """
        -- Rollback from Schema V2 to V1
        DROP TABLE IF EXISTS batch_uploads CASCADE;
        DROP TABLE IF EXISTS progress_records CASCADE;
        DROP TABLE IF EXISTS quiz_sessions CASCADE;
        DROP TABLE IF EXISTS tree_nodes CASCADE;
        
        -- Recreate legacy tables (simplified)
        CREATE TABLE domains (
            domain_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_by UUID REFERENCES users(id),
            is_public BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE terms (
            term_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
            term VARCHAR(255) NOT NULL,
            definition TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for database migrations
    
    Event structure:
    {
        "action": "migrate" | "rollback" | "validate" | "status",
        "target_version": "2.0.0",
        "applied_by": "deployment-pipeline"
    }
    """
    try:
        logger.info(f"Migration request: {json.dumps(event)}")
        
        action = event.get('action', 'status')
        migration_manager = MigrationManager()
        
        if action == 'migrate':
            target_version = event.get('target_version', '2.0.0')
            applied_by = event.get('applied_by', 'lambda')
            result = migration_manager.apply_migration(target_version, applied_by)
            
        elif action == 'rollback':
            target_version = event.get('target_version', '1.0.0')
            result = migration_manager.rollback_migration(target_version)
            
        elif action == 'validate':
            result = migration_manager.validate_schema()
            
        elif action == 'status':
            current_version = migration_manager.get_current_version()
            result = {
                'success': True,
                'current_version': current_version,
                'available_versions': list(migration_manager.migrations.keys())
            }
            
        else:
            raise ValueError(f"Unknown action: {action}")
        
        return create_response(200, result)
        
    except Exception as e:
        logger.error(f"Migration handler error: {e}")
        return handle_error(e, "Migration failed")


if __name__ == "__main__":
    # Test locally
    test_event = {
        "action": "migrate",
        "target_version": "2.0.0",
        "applied_by": "local-test"
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))