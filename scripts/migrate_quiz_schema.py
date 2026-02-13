#!/usr/bin/env python3
"""
Quiz Schema Migration Script
Validates and applies database schema for quiz engine deployment

This script uses shared migration logic with the Lambda function.

Usage:
    python scripts/migrate_quiz_schema.py --validate  # Check schema only
    python scripts/migrate_quiz_schema.py --apply     # Apply missing schema
"""
import os
import sys
import argparse
import logging
from typing import Dict

# Add Lambda function path to import shared migration logic
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'lambda_functions', 'db_schema_migration'))

from migration_manager import QuizSchemaMigration

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_validation_report(validation_results: Dict[str, bool]):
    """Print a formatted validation report"""
    print("\n" + "="*60)
    print("QUIZ SCHEMA VALIDATION REPORT")
    print("="*60)
    
    # Tables
    print("\nTables:")
    print(f"  quiz_sessions:     {'✓ EXISTS' if validation_results.get('quiz_sessions_table') else '✗ MISSING'}")
    print(f"  progress_records:  {'✓ EXISTS' if validation_results.get('progress_records_table') else '✗ MISSING'}")
    
    # Schema validation
    print("\nSchema Validation:")
    print(f"  quiz_sessions:     {'✓ VALID' if validation_results.get('quiz_sessions_schema') else '✗ INVALID'}")
    print(f"  progress_records:  {'✓ VALID' if validation_results.get('progress_records_schema') else '✗ INVALID'}")
    
    # Indexes
    print("\nIndexes:")
    index_keys = [k for k in validation_results.keys() if k.startswith('idx_')]
    for index_key in sorted(index_keys):
        status = '✓ EXISTS' if validation_results[index_key] else '✗ MISSING'
        print(f"  {index_key:30} {status}")
    
    # Summary
    all_valid = all(validation_results.values())
    print("\n" + "="*60)
    if all_valid:
        print("✓ ALL CHECKS PASSED - Schema is ready for quiz engine")
    else:
        print("✗ VALIDATION FAILED - Run with --apply to fix")
    print("="*60 + "\n")


def main():
    """Main entry point for migration script"""
    parser = argparse.ArgumentParser(
        description='Quiz Schema Migration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate schema only
  python scripts/migrate_quiz_schema.py --validate
  
  # Apply missing schema components
  python scripts/migrate_quiz_schema.py --apply
  
  # Use custom database connection
  DB_HOST=prod-db.example.com python scripts/migrate_quiz_schema.py --validate
        """
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate schema without making changes'
    )
    
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply missing schema components'
    )
    
    parser.add_argument(
        '--verify-permissions',
        action='store_true',
        help='Verify DB Proxy has required permissions'
    )
    
    args = parser.parse_args()
    
    # Require at least one action
    if not (args.validate or args.apply or args.verify_permissions):
        parser.error('At least one action required: --validate, --apply, or --verify-permissions')
    
    # Initialize migration manager
    try:
        migration = QuizSchemaMigration()
        migration.connect()
        
        # Validate schema
        if args.validate or args.apply:
            validation_results = migration.validate_schema()
            print_validation_report(validation_results)
            
            # Apply migration if requested and validation failed
            if args.apply:
                if not all(validation_results.values()):
                    logger.info("Applying migration to fix missing components...")
                    results = migration.apply_migration()
                    
                    print("\nMigration Results:")
                    if results['tables_created']:
                        print(f"  Tables created: {', '.join(results['tables_created'])}")
                    if results['indexes_created']:
                        print(f"  Indexes created: {', '.join(results['indexes_created'])}")
                    if results['errors']:
                        print(f"  Errors: {', '.join(results['errors'])}")
                        sys.exit(1)
                    
                    # Re-validate
                    print("\nRe-validating schema...")
                    validation_results = migration.validate_schema()
                    print_validation_report(validation_results)
                else:
                    logger.info("Schema is already valid, no migration needed")
        
        # Verify permissions
        if args.verify_permissions:
            print("\nVerifying DB Proxy Permissions...")
            has_permissions = migration.verify_db_proxy_permissions()
            if has_permissions:
                print("✓ DB Proxy has all required permissions")
            else:
                print("✗ DB Proxy missing required permissions")
                sys.exit(1)
        
        migration.disconnect()
        logger.info("Migration script completed successfully")
        
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
