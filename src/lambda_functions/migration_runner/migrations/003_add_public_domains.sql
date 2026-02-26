-- Migration: Add public domain support
-- Allows admin-uploaded domains to be shared with all users
-- Date: 2026-02-19

-- Add is_public column to tree_nodes (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tree_nodes' AND column_name = 'is_public'
    ) THEN
        ALTER TABLE tree_nodes 
        ADD COLUMN is_public BOOLEAN DEFAULT false NOT NULL;
    END IF;
END $$;

-- Create index for efficient public domain queries (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_tree_nodes_public'
    ) THEN
        CREATE INDEX idx_tree_nodes_public ON tree_nodes(is_public) 
        WHERE is_public = true;
    END IF;
END $$;

-- Create composite index for domain queries (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_tree_nodes_domain_access'
    ) THEN
        CREATE INDEX idx_tree_nodes_domain_access ON tree_nodes(node_type, user_id, is_public);
    END IF;
END $$;

-- Mark existing admin-uploaded domains as public
-- (Assumes admin user is in 'admin' Cognito group)
UPDATE tree_nodes 
SET is_public = true
WHERE node_type = 'domain'
AND user_id IN (
  SELECT id FROM users WHERE email = 'huschlej@comcast.net'
);

-- Verify migration
SELECT 
  node_type,
  is_public,
  COUNT(*) as count
FROM tree_nodes
GROUP BY node_type, is_public
ORDER BY node_type, is_public;
