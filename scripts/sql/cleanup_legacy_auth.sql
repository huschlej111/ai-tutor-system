-- Cleanup script for legacy authentication components
-- Removes JWT-related tables and functions that are no longer needed with Cognito

BEGIN;

-- Drop token blacklist table and related objects
DROP INDEX IF EXISTS idx_token_blacklist_jti;
DROP INDEX IF EXISTS idx_token_blacklist_user;
DROP INDEX IF EXISTS idx_token_blacklist_expires;

DROP FUNCTION IF EXISTS cleanup_expired_blacklisted_tokens();

DROP TABLE IF EXISTS token_blacklist;

-- Remove password_hash column from users table (make it optional for migration)
-- Note: We keep the column for now in case there's a rollback need
-- ALTER TABLE users DROP COLUMN IF EXISTS password_hash;

-- Add comment to indicate the column is deprecated
COMMENT ON COLUMN users.password_hash IS 'DEPRECATED: Password authentication replaced by AWS Cognito. This column will be removed in a future migration.';

COMMIT;