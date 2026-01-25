-- Rollback from Schema V2 to V1
-- Safely removes tree-based architecture and restores legacy tables
-- Use with caution - this will result in data loss

BEGIN;

-- Drop V2 tables in correct order (respecting foreign keys)
DROP TABLE IF EXISTS batch_uploads CASCADE;
DROP TABLE IF EXISTS progress_records CASCADE;
DROP TABLE IF EXISTS quiz_sessions CASCADE;
DROP TABLE IF EXISTS tree_nodes CASCADE;

-- Drop V2 specific functions
DROP FUNCTION IF EXISTS validate_domain_data(JSONB);
DROP FUNCTION IF EXISTS validate_term_data(JSONB);

-- Recreate legacy V1 tables for backward compatibility
CREATE TABLE IF NOT EXISTS domains (
    domain_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by UUID REFERENCES users(id),
    is_public BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS terms (
    term_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    term VARCHAR(255) NOT NULL,
    definition TEXT NOT NULL,
    examples TEXT[],
    difficulty_level INTEGER DEFAULT 1 CHECK (difficulty_level BETWEEN 1 AND 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(domain_id, term)
);

CREATE TABLE IF NOT EXISTS user_progress (
    progress_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    term_id UUID REFERENCES terms(term_id) ON DELETE CASCADE,
    correct_answers INTEGER DEFAULT 0,
    total_attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMP WITH TIME ZONE,
    mastery_level DECIMAL(3,2) DEFAULT 0.0 CHECK (mastery_level BETWEEN 0.0 AND 1.0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, domain_id, term_id)
);

-- Recreate V1 indexes
CREATE INDEX IF NOT EXISTS idx_domains_created_by ON domains(created_by);
CREATE INDEX IF NOT EXISTS idx_terms_domain_id ON terms(domain_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_user_domain ON user_progress(user_id, domain_id);

-- Recreate V1 triggers
CREATE TRIGGER update_domains_updated_at BEFORE UPDATE ON domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_terms_updated_at BEFORE UPDATE ON terms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_progress_updated_at BEFORE UPDATE ON user_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;