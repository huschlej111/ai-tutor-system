# Database Migrations

Automated database migration system for the Know-It-All Tutor System.

## Overview

Migrations are automatically applied during CDK deployment via a Lambda function that:
1. Reads migration files embedded in the Lambda package
2. Checks which migrations have been applied (tracked in `schema_migrations` table)
3. Applies pending migrations in order
4. Records success/failure with timestamps and checksums

## Migration Files

Location: `database/migrations/`

Naming convention: `{version}_{description}.sql`
- Version: 3-digit number (e.g., `001`, `002`, `003`)
- Description: Snake_case description
- Example: `001_create_users_table.sql`

**Important:** Version `000` is reserved for the migrations tracking table itself.

## How It Works

### Automatic Deployment
```bash
cd infrastructure
cdk deploy BackendStack-dev
```

The migration runner Lambda is triggered automatically via CloudFormation Custom Resource:
1. On stack creation (first deployment)
2. On stack updates (subsequent deployments)

### Manual Execution

Check migration status:
```bash
aws lambda invoke \
  --function-name BackendStack-dev-MigrationRunnerFunction \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action": "status"}' \
  /tmp/migration-status.json && cat /tmp/migration-status.json
```

Run migrations manually:
```bash
aws lambda invoke \
  --function-name BackendStack-dev-MigrationRunnerFunction \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action": "migrate"}' \
  /tmp/migration-result.json && cat /tmp/migration-result.json
```

Dry run (see what would be applied):
```bash
aws lambda invoke \
  --function-name BackendStack-dev-MigrationRunnerFunction \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action": "migrate", "dry_run": true}' \
  /tmp/migration-dryrun.json && cat /tmp/migration-dryrun.json
```

## Creating New Migrations

1. **Create migration file:**
   ```bash
   # Find next version number
   ls database/migrations/ | sort | tail -1
   
   # Create new migration
   touch database/migrations/004_add_new_feature.sql
   ```

2. **Write SQL:**
   ```sql
   -- Migration: Add new feature
   -- Date: 2026-02-19
   
   ALTER TABLE users ADD COLUMN new_field VARCHAR(255);
   CREATE INDEX idx_users_new_field ON users(new_field);
   ```

3. **Test locally (optional):**
   ```bash
   # Connect to local database
   psql -h localhost -U tutor_admin -d tutor_system
   
   # Run migration SQL manually
   \i database/migrations/004_add_new_feature.sql
   ```

4. **Deploy:**
   ```bash
   cd infrastructure
   cdk deploy BackendStack-dev
   ```
   
   The migration will be automatically applied during deployment.

## Migration Tracking

All applied migrations are recorded in the `schema_migrations` table:

```sql
SELECT * FROM schema_migrations ORDER BY applied_at DESC;
```

Columns:
- `version`: Migration version (e.g., "003")
- `name`: Migration filename without extension
- `applied_at`: Timestamp when applied
- `checksum`: SHA256 hash of migration content
- `execution_time_ms`: How long it took to run
- `success`: Whether it succeeded

## Best Practices

### DO:
- ✅ Use sequential version numbers (001, 002, 003...)
- ✅ Make migrations idempotent when possible (`CREATE TABLE IF NOT EXISTS`)
- ✅ Test migrations on a copy of production data
- ✅ Keep migrations small and focused
- ✅ Add comments explaining what and why
- ✅ Include both schema changes and data migrations in same file if related

### DON'T:
- ❌ Modify existing migration files after they've been applied
- ❌ Skip version numbers
- ❌ Put multiple unrelated changes in one migration
- ❌ Forget to add indexes for new columns used in WHERE clauses
- ❌ Use DROP TABLE without careful consideration

## Rollback Strategy

Currently, rollbacks are manual. To rollback a migration:

1. **Create a new migration** that reverses the changes:
   ```sql
   -- Migration: Rollback feature X
   -- Reverses: 004_add_new_feature.sql
   
   DROP INDEX IF EXISTS idx_users_new_field;
   ALTER TABLE users DROP COLUMN IF EXISTS new_field;
   ```

2. **Deploy the rollback migration** like any other migration

**Future Enhancement:** Add "down" migrations for automatic rollback.

## Troubleshooting

### Migration Failed During Deployment

1. Check CloudWatch logs:
   ```bash
   aws logs tail /aws/lambda/BackendStack-dev-MigrationRunnerFunction --since 10m
   ```

2. Check migration status:
   ```bash
   aws lambda invoke \
     --function-name BackendStack-dev-MigrationRunnerFunction \
     --cli-binary-format raw-in-base64-out \
     --payload '{"action": "status"}' \
     /tmp/status.json && cat /tmp/status.json
   ```

3. Fix the migration file and redeploy

### Migration Stuck or Timeout

- Increase Lambda timeout in `backend_stack.py` (currently 300 seconds)
- Break large migrations into smaller chunks
- Consider running data migrations separately from schema changes

### Need to Re-run a Migration

Migrations are tracked by version. To re-run:

1. Delete the record from `schema_migrations`:
   ```sql
   DELETE FROM schema_migrations WHERE version = '004';
   ```

2. Redeploy or manually invoke migration runner

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CDK Deployment                          │
│                                                             │
│  1. Deploy Migration Runner Lambda                         │
│     - Embeds all .sql files from database/migrations/      │
│     - Has VPC access to RDS                                │
│                                                             │
│  2. Trigger Custom Resource                                │
│     - Invokes Migration Runner Lambda                      │
│     - Waits for completion                                 │
│     - Fails deployment if migrations fail                  │
│                                                             │
│  3. Deploy Application Lambdas                             │
│     - Only after migrations succeed                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Migration Runner Lambda                        │
│                                                             │
│  1. Read embedded migration files                          │
│  2. Query schema_migrations table                          │
│  3. Calculate pending migrations                           │
│  4. Apply each migration in order                          │
│  5. Record results in schema_migrations                    │
│  6. Stop on first failure                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Future Enhancements

- [ ] Add "down" migrations for automatic rollback
- [ ] Add migration validation (syntax check before apply)
- [ ] Add migration dependencies (require certain migrations before others)
- [ ] Add migration dry-run in CI/CD pipeline
- [ ] Add Slack/SNS notifications for migration failures
- [ ] Add migration performance metrics to CloudWatch
- [ ] Support for data-only migrations (no schema changes)
- [ ] Migration preview in pull requests

## Related Files

- `database/migrations/*.sql` - Migration files
- `src/lambda_functions/migration_runner/handler.py` - Migration runner code
- `infrastructure/stacks/backend_stack.py` - CDK integration
- `lambda_layer/python/database.py` - Database connection utilities
