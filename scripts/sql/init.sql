-- Initialize PostgreSQL database for local development
-- This script runs automatically when the PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Create domains table
CREATE TABLE IF NOT EXISTS domains (
    domain_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by UUID REFERENCES users(user_id),
    is_public BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create terms table
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

-- Create user_progress table
CREATE TABLE IF NOT EXISTS user_progress (
    progress_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
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

-- Create quiz_sessions table
CREATE TABLE IF NOT EXISTS quiz_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    domain_id UUID REFERENCES domains(domain_id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    session_data JSONB
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_domains_created_by ON domains(created_by);
CREATE INDEX IF NOT EXISTS idx_terms_domain_id ON terms(domain_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_user_domain ON user_progress(user_id, domain_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user_id ON quiz_sessions(user_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_domains_updated_at BEFORE UPDATE ON domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_terms_updated_at BEFORE UPDATE ON terms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_progress_updated_at BEFORE UPDATE ON user_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for development
INSERT INTO users (email, password_hash, first_name, last_name, is_verified) VALUES
    ('admin@example.com', crypt('admin123', gen_salt('bf')), 'Admin', 'User', true),
    ('test@example.com', crypt('test123', gen_salt('bf')), 'Test', 'User', true)
ON CONFLICT (email) DO NOTHING;

-- Insert sample domain
INSERT INTO domains (name, description, created_by, is_public) VALUES
    ('AWS Fundamentals', 'Basic AWS concepts and services', 
     (SELECT user_id FROM users WHERE email = 'admin@example.com'), true)
ON CONFLICT DO NOTHING;

-- Insert sample terms
INSERT INTO terms (domain_id, term, definition, examples, difficulty_level) VALUES
    ((SELECT domain_id FROM domains WHERE name = 'AWS Fundamentals'), 
     'EC2', 'Elastic Compute Cloud - Virtual servers in the cloud', 
     ARRAY['t2.micro', 't3.small', 'm5.large'], 1),
    ((SELECT domain_id FROM domains WHERE name = 'AWS Fundamentals'), 
     'S3', 'Simple Storage Service - Object storage service', 
     ARRAY['Buckets', 'Objects', 'Versioning'], 1),
    ((SELECT domain_id FROM domains WHERE name = 'AWS Fundamentals'), 
     'Lambda', 'Serverless compute service that runs code in response to events', 
     ARRAY['Event-driven', 'Pay-per-use', 'Auto-scaling'], 2)
ON CONFLICT (domain_id, term) DO NOTHING;

COMMIT;