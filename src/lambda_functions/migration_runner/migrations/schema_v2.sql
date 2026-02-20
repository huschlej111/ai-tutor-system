-- Database Schema V2: Tree-based Domain-Agnostic Architecture (Cognito-enabled)
-- Implements tree_nodes table design for domain-agnostic content management
-- Uses AWS Cognito for authentication (no password_hash)

-- Create extensions for UUID and JSONB support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (Cognito-integrated)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cognito_sub VARCHAR(255) UNIQUE NOT NULL,  -- Cognito user ID (was cognito_user_id)
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Generic tree nodes table with JSONB for domain-agnostic content
-- This is the core innovation - all content stored as tree structures
CREATE TABLE IF NOT EXISTS tree_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_id UUID REFERENCES tree_nodes(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) NOT NULL,
    node_type VARCHAR(50) NOT NULL CHECK (node_type IN ('domain', 'category', 'term')),
    data JSONB NOT NULL,                    -- Domain-specific payload
    metadata JSONB DEFAULT '{}',            -- Structural metadata
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

-- Progress tracking table
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

-- Batch upload records table
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

-- Performance indexes for tree traversal optimization
CREATE INDEX IF NOT EXISTS idx_tree_nodes_parent ON tree_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_user ON tree_nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_type ON tree_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_user_type ON tree_nodes(user_id, node_type);

-- JSONB content search optimization using GIN indexes
CREATE INDEX IF NOT EXISTS idx_tree_nodes_data_gin ON tree_nodes USING GIN (data);
CREATE INDEX IF NOT EXISTS idx_tree_nodes_metadata_gin ON tree_nodes USING GIN (metadata);

-- Progress tracking optimization
CREATE INDEX IF NOT EXISTS idx_progress_user_term ON progress_records(user_id, term_id);
CREATE INDEX IF NOT EXISTS idx_progress_session ON progress_records(session_id);
CREATE INDEX IF NOT EXISTS idx_progress_user_created ON progress_records(user_id, created_at);

-- Quiz sessions optimization
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_domain ON quiz_sessions(domain_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_status ON quiz_sessions(status);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user_status ON quiz_sessions(user_id, status);

-- Batch uploads optimization
CREATE INDEX IF NOT EXISTS idx_batch_uploads_admin ON batch_uploads(admin_id);
CREATE INDEX IF NOT EXISTS idx_batch_uploads_status ON batch_uploads(status);

-- User table optimization
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_cognito_sub ON users(cognito_sub);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_tree_nodes_updated_at ON tree_nodes;
CREATE TRIGGER update_tree_nodes_updated_at 
    BEFORE UPDATE ON tree_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Validation functions for JSONB data integrity
CREATE OR REPLACE FUNCTION validate_domain_data(data JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Domain nodes must have name and description
    RETURN (data ? 'name' AND data ? 'description');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validate_term_data(data JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Term nodes must have term and definition
    RETURN (data ? 'term' AND data ? 'definition');
END;
$$ LANGUAGE plpgsql;

-- Add constraints for data validation
ALTER TABLE tree_nodes ADD CONSTRAINT check_domain_data 
    CHECK (node_type != 'domain' OR validate_domain_data(data));

ALTER TABLE tree_nodes ADD CONSTRAINT check_term_data 
    CHECK (node_type != 'term' OR validate_term_data(data));

-- Add constraint to ensure domains have no parent
ALTER TABLE tree_nodes ADD CONSTRAINT check_domain_no_parent 
    CHECK (node_type != 'domain' OR parent_id IS NULL);

-- Add constraint to ensure terms have a parent (domain or category)
ALTER TABLE tree_nodes ADD CONSTRAINT check_term_has_parent 
    CHECK (node_type != 'term' OR parent_id IS NOT NULL);

COMMIT;