-- Migration script to update existing database to V2 schema
-- Handles the transition from legacy schema to tree-based architecture

BEGIN;

-- First, update the users table to use 'id' instead of 'user_id'
-- Check if we need to rename the column
DO $$
BEGIN
    -- Check if user_id column exists and id doesn't
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'users' AND column_name = 'user_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'users' AND column_name = 'id') THEN
        
        -- Rename user_id to id
        ALTER TABLE users RENAME COLUMN user_id TO id;
        
        -- Update any existing foreign key references
        -- This will be handled by the constraint recreation below
        
    END IF;
END $$;

-- Drop existing tables that will be replaced by tree_nodes
DROP TABLE IF EXISTS user_progress CASCADE;
DROP TABLE IF EXISTS terms CASCADE;
DROP TABLE IF EXISTS domains CASCADE;

-- Create tree_nodes table
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

-- Update quiz_sessions table to reference tree_nodes
-- First drop the existing foreign key constraint if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.table_constraints 
               WHERE constraint_name = 'quiz_sessions_domain_id_fkey' 
               AND table_name = 'quiz_sessions') THEN
        ALTER TABLE quiz_sessions DROP CONSTRAINT quiz_sessions_domain_id_fkey;
    END IF;
END $$;

-- Add missing columns to quiz_sessions if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'quiz_sessions' AND column_name = 'domain_id') THEN
        ALTER TABLE quiz_sessions ADD COLUMN domain_id UUID;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'quiz_sessions' AND column_name = 'status') THEN
        ALTER TABLE quiz_sessions ADD COLUMN status VARCHAR(20) DEFAULT 'active';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'quiz_sessions' AND column_name = 'current_term_index') THEN
        ALTER TABLE quiz_sessions ADD COLUMN current_term_index INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'quiz_sessions' AND column_name = 'paused_at') THEN
        ALTER TABLE quiz_sessions ADD COLUMN paused_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'quiz_sessions' AND column_name = 'session_data') THEN
        ALTER TABLE quiz_sessions ADD COLUMN session_data JSONB DEFAULT '{}';
    END IF;
END $$;

-- Add constraint for status column
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints 
                   WHERE constraint_name = 'quiz_sessions_status_check') THEN
        ALTER TABLE quiz_sessions ADD CONSTRAINT quiz_sessions_status_check 
            CHECK (status IN ('active', 'paused', 'completed', 'abandoned'));
    END IF;
END $$;

-- Create progress_records table
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

-- Create batch_uploads table
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

-- Create all indexes
CREATE INDEX IF NOT EXISTS idx_tree_nodes_parent ON tree_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_user ON tree_nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_type ON tree_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_user_type ON tree_nodes(user_id, node_type);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_data_gin ON tree_nodes USING GIN (data);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_metadata_gin ON tree_nodes USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_progress_user_term ON progress_records(user_id, term_id);
CREATE INDEX IF NOT EXISTS idx_progress_session ON progress_records(session_id);
CREATE INDEX IF NOT EXISTS idx_progress_user_created ON progress_records(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_domain ON quiz_sessions(domain_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_status ON quiz_sessions(status);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user_status ON quiz_sessions(user_id, status);

CREATE INDEX IF NOT EXISTS idx_batch_uploads_admin ON batch_uploads(admin_id);
CREATE INDEX IF NOT EXISTS idx_batch_uploads_status ON batch_uploads(status);

-- Add foreign key constraint for quiz_sessions.domain_id
ALTER TABLE quiz_sessions ADD CONSTRAINT quiz_sessions_domain_id_fkey 
    FOREIGN KEY (domain_id) REFERENCES tree_nodes(id);

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_tree_nodes_updated_at ON tree_nodes;
CREATE TRIGGER update_tree_nodes_updated_at 
    BEFORE UPDATE ON tree_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Validation functions for JSONB data integrity
CREATE OR REPLACE FUNCTION validate_domain_data(data JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (data ? 'name' AND data ? 'description');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validate_term_data(data JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (data ? 'term' AND data ? 'definition');
END;
$$ LANGUAGE plpgsql;

-- Add constraints for data validation
ALTER TABLE tree_nodes ADD CONSTRAINT check_domain_data 
    CHECK (node_type != 'domain' OR validate_domain_data(data));

ALTER TABLE tree_nodes ADD CONSTRAINT check_term_data 
    CHECK (node_type != 'term' OR validate_term_data(data));

ALTER TABLE tree_nodes ADD CONSTRAINT check_domain_no_parent 
    CHECK (node_type != 'domain' OR parent_id IS NULL);

ALTER TABLE tree_nodes ADD CONSTRAINT check_term_has_parent 
    CHECK (node_type != 'term' OR parent_id IS NOT NULL);

COMMIT;