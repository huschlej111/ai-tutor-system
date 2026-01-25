-- Migration script to support AWS Cognito authentication
-- Adds Cognito user ID and auth logs table

BEGIN;

-- Add Cognito user ID to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS cognito_user_id VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;

-- Make password_hash optional since Cognito handles authentication
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- Create auth logs table for security monitoring
CREATE TABLE IF NOT EXISTS auth_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cognito_user_id VARCHAR(255),
    email VARCHAR(255),
    event_type VARCHAR(50) NOT NULL,
    trigger_source VARCHAR(100),
    client_metadata JSONB DEFAULT '{}',
    success BOOLEAN NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for auth logs
CREATE INDEX IF NOT EXISTS idx_auth_logs_cognito_user ON auth_logs(cognito_user_id);
CREATE INDEX IF NOT EXISTS idx_auth_logs_email ON auth_logs(email);
CREATE INDEX IF NOT EXISTS idx_auth_logs_event_type ON auth_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_auth_logs_created_at ON auth_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_auth_logs_success ON auth_logs(success);

-- Add index for Cognito user ID lookup
CREATE INDEX IF NOT EXISTS idx_users_cognito_user_id ON users(cognito_user_id);

-- Update trigger for users table to handle last_login_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;