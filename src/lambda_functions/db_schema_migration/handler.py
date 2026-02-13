"""
Database Schema Migration Lambda Function
Invoked by CI/CD pipeline to apply schema changes automatically

This Lambda wraps the migration logic for automated deployment.
It can be invoked by:
1. CI/CD pipeline (CodeBuild/CodePipeline)
2. Manual invocation for testing
3. CloudFormation Custom Resource (future)

Event structure:
{
    "action": "validate" | "apply" | "verify-permissions",
    "dry_run": true | false
}
"""
import json
import os
import sys
import logging
from typing import Dict, Any
import boto3

# Add shared modules to path
sys.path.append('/opt/python')

# Import the migration logic
sys.path.append(os.path.dirname(__file__))
from migration_manager import QuizSchemaMigration

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for database schema migrations.
    
    Args:
        event: Lambda event with action and parameters
        context: Lambda context
        
    Returns:
        Migration results with status and details
    """
    try:
        logger.info(f"Schema migration request: {json.dumps(event)}")
        
        action = event.get('action', 'validate')
        dry_run = event.get('dry_run', False)
        
        # Initialize migration manager
        # It will automatically get DB config from Secrets Manager or environment
        migration = QuizSchemaMigration()
        migration.connect()
        
        result = {
            'success': False,
            'action': action,
            'dry_run': dry_run,
            'environment': os.getenv('ENVIRONMENT', 'unknown')
        }
        
        try:
            if action == 'validate':
                # Validate schema without making changes
                validation_results = migration.validate_schema()
                all_valid = all(validation_results.values())
                
                result['success'] = True
                result['validation'] = validation_results
                result['schema_valid'] = all_valid
                result['message'] = 'Schema validation complete'
                
                if not all_valid:
                    missing_components = [k for k, v in validation_results.items() if not v]
                    result['missing_components'] = missing_components
                    result['message'] = f'Schema validation failed: {len(missing_components)} components missing'
                
            elif action == 'apply':
                # Apply migration
                if dry_run:
                    # Dry run: validate only
                    validation_results = migration.validate_schema()
                    result['success'] = True
                    result['validation'] = validation_results
                    result['message'] = 'Dry run complete - no changes made'
                else:
                    # Real migration
                    migration_results = migration.apply_migration()
                    result['success'] = len(migration_results.get('errors', [])) == 0
                    result['migration'] = migration_results
                    
                    if result['success']:
                        result['message'] = 'Migration applied successfully'
                    else:
                        result['message'] = f"Migration failed: {migration_results['errors']}"
                
            elif action == 'verify-permissions':
                # Verify DB Proxy has required permissions
                has_permissions = migration.verify_db_proxy_permissions()
                result['success'] = has_permissions
                result['permissions_valid'] = has_permissions
                result['message'] = 'Permissions verified' if has_permissions else 'Permission verification failed'
                
            else:
                result['success'] = False
                result['message'] = f'Unknown action: {action}'
            
        finally:
            migration.disconnect()
        
        logger.info(f"Migration result: {json.dumps(result)}")
        return result
        
    except Exception as e:
        logger.error(f"Migration handler error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': f'Migration failed with error: {str(e)}'
        }


def invoke_from_pipeline(environment: str = None) -> Dict[str, Any]:
    """
    Helper function for CI/CD pipeline invocation.
    Can be called from buildspec.yml or deployment scripts.
    
    Args:
        environment: Target environment (development, staging, production)
        
    Returns:
        Migration results
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development')
    
    # Get Lambda function name
    function_name = f"tutor-db-migrate-{environment}"
    
    # Invoke Lambda
    lambda_client = boto3.client('lambda')
    
    try:
        # First validate
        logger.info(f"Validating schema in {environment}...")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps({'action': 'validate'})
        )
        
        validation_result = json.loads(response['Payload'].read())
        
        if not validation_result.get('schema_valid', False):
            # Schema needs migration
            logger.info(f"Schema validation failed, applying migration...")
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps({'action': 'apply', 'dry_run': False})
            )
            
            migration_result = json.loads(response['Payload'].read())
            return migration_result
        else:
            logger.info("Schema is already valid, no migration needed")
            return validation_result
            
    except Exception as e:
        logger.error(f"Pipeline invocation failed: {e}")
        raise


if __name__ == '__main__':
    # Test locally
    test_event = {
        'action': 'validate'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
