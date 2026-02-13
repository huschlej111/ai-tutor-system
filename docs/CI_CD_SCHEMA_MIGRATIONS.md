# CI/CD Schema Migration Strategy

## Overview

This document explains how database schema changes flow through the CI/CD pipeline for the Know-It-All Tutor system.

## Architecture

### Components

1. **Shared Migration Logic** (`src/lambda_functions/db_schema_migration/migration_manager.py`)
   - Core migration logic used by both Lambda and standalone script
   - Validates schema, applies changes, verifies permissions
   - Idempotent - safe to run multiple times

2. **DB Migration Lambda** (`src/lambda_functions/db_schema_migration/handler.py`)
   - Invoked automatically by CI/CD pipeline
   - Wraps migration logic for automated deployment
   - Returns structured results for pipeline validation

3. **Standalone Script** (`scripts/migrate_quiz_schema.py`)
   - Manual execution for development/testing
   - Uses same shared logic as Lambda
   - Provides detailed console output

## CI/CD Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Developer pushes code to GitHub (main/develop branch)   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CodePipeline triggers (webhook)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CodeBuild: Build & Test Stage                            │
│    - Run unit tests                                          │
│    - Run integration tests                                   │
│    - Package Lambda functions                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Manual Approval (Production only)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. CodeBuild: Deploy Stage                                  │
│    a. CDK bootstrap                                          │
│    b. CDK deploy (infrastructure + Lambda functions)        │
│    c. Invoke DB Migration Lambda ← SCHEMA CHANGES HERE      │
│    d. Post-deployment validation                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Deployment Complete                                       │
│    - CloudWatch metrics updated                              │
│    - SNS notifications sent                                  │
└─────────────────────────────────────────────────────────────┘
```

## How Schema Changes Are Applied

### Step 1: Developer Makes Schema Changes

Developer updates the migration logic in `migration_manager.py`:

```python
# Example: Adding a new column to quiz_sessions
def _create_quiz_sessions_table(self):
    self.cursor.execute("""
        CREATE TABLE quiz_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id),
            domain_id UUID NOT NULL REFERENCES tree_nodes(id),
            status VARCHAR(20) DEFAULT 'active',
            current_term_index INTEGER DEFAULT 0,
            total_terms INTEGER NOT NULL,
            difficulty_level VARCHAR(20),  # ← NEW COLUMN
            started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            ...
        )
    """)
```

### Step 2: Test Locally

```bash
# Test migration locally before pushing
python scripts/migrate_quiz_schema.py --validate
python scripts/migrate_quiz_schema.py --apply
```

### Step 3: Push to GitHub

```bash
git add src/lambda_functions/db_schema_migration/migration_manager.py
git commit -m "Add difficulty_level column to quiz_sessions"
git push origin develop
```

### Step 4: Pipeline Executes

The CodeBuild deploy stage runs:

```yaml
build:
  commands:
    - echo 'Deploying infrastructure...'
    - cdk deploy --all --require-approval never
    
    - echo 'Running database migrations...'
    - aws lambda invoke \
        --function-name tutor-db-migrate-$ENVIRONMENT \
        --payload '{"action":"validate"}' \
        /tmp/migration-result.json
    
    - cat /tmp/migration-result.json
    
    # If validation fails, apply migration
    - |
      if grep -q '"schema_valid":false' /tmp/migration-result.json; then
        echo "Schema validation failed, applying migration..."
        aws lambda invoke \
          --function-name tutor-db-migrate-$ENVIRONMENT \
          --payload '{"action":"apply","dry_run":false}' \
          /tmp/migration-result.json
        cat /tmp/migration-result.json
      fi
```

### Step 5: Migration Lambda Executes

The Lambda function:
1. Connects to RDS using Secrets Manager credentials
2. Validates current schema
3. Applies missing components (tables, columns, indexes)
4. Returns results to CodeBuild

### Step 6: Pipeline Validates Results

CodeBuild checks the Lambda response:
- If `success: true` → Continue deployment
- If `success: false` → Fail pipeline, rollback

## Migration Safety Features

### 1. Idempotency

All migration operations use `IF NOT EXISTS`:

```sql
CREATE TABLE IF NOT EXISTS quiz_sessions (...);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id);
ALTER TABLE quiz_sessions ADD COLUMN IF NOT EXISTS difficulty_level VARCHAR(20);
```

### 2. Transaction Safety

Migrations run in transactions with automatic rollback on error:

```python
try:
    self.conn.autocommit = False
    # Apply all changes
    self.conn.commit()
except Exception as e:
    self.conn.rollback()
    raise
```

### 3. Validation Before Apply

Always validate before applying:

```python
# 1. Validate
validation_results = migration.validate_schema()

# 2. Only apply if needed
if not all(validation_results.values()):
    migration.apply_migration()
```

### 4. Dry Run Support

Test migrations without making changes:

```python
# Lambda event
{
    "action": "apply",
    "dry_run": true  # ← No changes made
}
```

## Environment-Specific Migrations

### Development Environment

```bash
# Automatic on every push to develop branch
# No manual approval required
# Fast feedback loop
```

### Staging Environment

```bash
# Automatic on merge to staging branch
# Mirrors production configuration
# Final validation before production
```

### Production Environment

```bash
# Requires manual approval
# SNS notification sent to ops team
# Migration runs after approval
# CloudWatch alarms monitor for issues
```

## Adding New Schema Changes

### Example: Adding a New Table

1. **Update migration_manager.py**:

```python
def _create_quiz_analytics_table(self):
    """Create quiz_analytics table"""
    logger.info("Creating quiz_analytics table...")
    self.cursor.execute("""
        CREATE TABLE quiz_analytics (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES quiz_sessions(id),
            metric_name VARCHAR(100) NOT NULL,
            metric_value DECIMAL(10,2),
            recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("quiz_analytics table created")

def apply_migration(self):
    # ... existing code ...
    
    # Add new table creation
    if not self._check_table_exists('quiz_analytics'):
        self._create_quiz_analytics_table()
        results['tables_created'].append('quiz_analytics')
```

2. **Update validation**:

```python
def validate_schema(self):
    # ... existing code ...
    
    # Add new table validation
    validation_results['quiz_analytics_table'] = self._check_table_exists('quiz_analytics')
```

3. **Test locally**:

```bash
python scripts/migrate_quiz_schema.py --validate
python scripts/migrate_quiz_schema.py --apply
```

4. **Push to GitHub** - Pipeline handles the rest!

## Rollback Strategy

### Automatic Rollback

If migration fails, CodeBuild fails the deployment:
- CloudFormation stack remains at previous version
- Database changes are rolled back (transaction)
- No partial state

### Manual Rollback

If you need to rollback a successful migration:

```bash
# 1. Revert code changes
git revert <commit-hash>
git push origin main

# 2. Pipeline redeploys previous version
# 3. Migration Lambda validates schema
# 4. No changes needed (idempotent)
```

### Data Preservation

Migrations never delete data:
- `CREATE TABLE IF NOT EXISTS` - Safe
- `ALTER TABLE ADD COLUMN` - Safe
- `CREATE INDEX` - Safe
- `DROP TABLE` - NEVER used in migrations

## Monitoring

### CloudWatch Logs

Migration Lambda logs all operations:

```
2026-02-12 10:15:23 INFO Quiz Schema Migration initialized
2026-02-12 10:15:24 INFO Connected to database: tutor_system
2026-02-12 10:15:24 INFO Starting schema validation...
2026-02-12 10:15:24 INFO Table 'quiz_sessions': EXISTS
2026-02-12 10:15:24 INFO Table 'progress_records': EXISTS
2026-02-12 10:15:25 INFO Schema validation complete. All valid: True
```

### CloudWatch Metrics

Pipeline creates custom metrics:
- `MigrationSuccess` - Count of successful migrations
- `MigrationFailure` - Count of failed migrations
- `MigrationDuration` - Time taken for migration

### CloudWatch Alarms

Alarms trigger on:
- Migration failure
- Migration duration > 5 minutes
- Database connection errors

## Best Practices

1. **Always test locally first**
   ```bash
   python scripts/migrate_quiz_schema.py --validate
   python scripts/migrate_quiz_schema.py --apply
   ```

2. **Use feature branches**
   ```bash
   git checkout -b feature/add-quiz-analytics
   # Make changes
   git push origin feature/add-quiz-analytics
   # Create PR for review
   ```

3. **Add validation for new components**
   - Every new table needs validation logic
   - Every new index needs validation logic

4. **Document schema changes**
   - Update data model documentation
   - Add comments in migration code
   - Update API documentation if schema affects endpoints

5. **Monitor after deployment**
   - Check CloudWatch logs
   - Verify metrics
   - Test affected endpoints

## Troubleshooting

### Migration Fails in Pipeline

1. Check CloudWatch logs for the migration Lambda
2. Look for SQL errors or connection issues
3. Verify Secrets Manager has correct credentials
4. Check RDS security groups allow Lambda access

### Schema Validation Fails

1. Run standalone script to see detailed output:
   ```bash
   python scripts/migrate_quiz_schema.py --validate
   ```

2. Check which components are missing
3. Verify database user has required permissions

### Permission Issues

1. Verify DB Proxy permissions:
   ```bash
   python scripts/migrate_quiz_schema.py --verify-permissions
   ```

2. Check IAM role for migration Lambda
3. Verify database user grants

## References

- [Pipeline Stack](../infrastructure/stacks/pipeline_stack.py)
- [Migration Manager](../src/lambda_functions/db_schema_migration/migration_manager.py)
- [Migration Lambda](../src/lambda_functions/db_schema_migration/handler.py)
- [Standalone Script](../scripts/migrate_quiz_schema.py)
