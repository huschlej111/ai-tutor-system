-- One-time setup for Gitea CI host-runner tests.
-- Run as the postgres superuser:
--   sudo -u postgres psql -f scripts/sql/setup-ci-testdb.sql
--
-- Note: CREATE DATABASE cannot run inside a transaction, so this script
-- uses IF NOT EXISTS patterns where supported and relies on psql's
-- \gexec trick for the database creation.

-- Create role if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'testuser') THEN
    CREATE ROLE testuser WITH LOGIN PASSWORD 'testpassword';
    RAISE NOTICE 'Created role testuser';
  ELSE
    RAISE NOTICE 'Role testuser already exists';
  END IF;
END
$$;

-- Create database if it doesn't exist (uses \gexec outside a transaction)
SELECT 'CREATE DATABASE tutor_system_test OWNER testuser'
  WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'tutor_system_test')
\gexec

-- Grant all privileges on the database
GRANT ALL PRIVILEGES ON DATABASE tutor_system_test TO testuser;

\echo 'Setup complete. Verify with:'
\echo '  psql postgresql://testuser:testpassword@localhost:5432/tutor_system_test -c \\conninfo'
