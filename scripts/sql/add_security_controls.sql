-- Add security controls tables for authentication hardening
-- Rate limiting, brute force protection, account lockout, and audit logging

-- Rate limiting table for tracking authentication attempts
CREATE TABLE IF NOT EXISTS auth_rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identifier VARCHAR(255) NOT NULL,  -- IP address or email
    identifier_type VARCHAR(20) NOT NULL CHECK (identifier_type IN ('ip', 'email')),
    attempt_count INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    blocked_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Account lockout table for tracking locked accounts
CREATE TABLE IF NOT EXISTS account_lockouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    failed_attempts INTEGER DEFAULT 0,
    locked_at TIMESTAMP WITH TIME ZONE,
    locked_until TIMESTAMP WITH TIME ZONE,
    unlock_token VARCHAR(255),  -- For manual unlock
    lockout_reason VARCHAR(100) DEFAULT 'failed_attempts',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Security audit log for authentication events
CREATE TABLE IF NOT EXISTS auth_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    event_type VARCHAR(50) NOT NULL,  -- login_success, login_failed, register, logout, etc.
    event_details JSONB DEFAULT '{}',
    risk_score INTEGER DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TOTP (Two-Factor Authentication) preparation table
CREATE TABLE IF NOT EXISTS user_totp (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    secret_key VARCHAR(255) NOT NULL,  -- Base32 encoded secret
    is_enabled BOOLEAN DEFAULT false,
    backup_codes TEXT[],  -- Array of backup codes
    last_used_code VARCHAR(10),  -- Prevent code reuse
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_identifier ON auth_rate_limits(identifier, identifier_type);
CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_window ON auth_rate_limits(window_start);
CREATE INDEX IF NOT EXISTS idx_account_lockouts_user ON account_lockouts(user_id);
CREATE INDEX IF NOT EXISTS idx_account_lockouts_email ON account_lockouts(email);
CREATE INDEX IF NOT EXISTS idx_auth_audit_log_user ON auth_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_log_email ON auth_audit_log(email);
CREATE INDEX IF NOT EXISTS idx_auth_audit_log_ip ON auth_audit_log(ip_address);
CREATE INDEX IF NOT EXISTS idx_auth_audit_log_event ON auth_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_auth_audit_log_created ON auth_audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_user_totp_user ON user_totp(user_id);

-- Add updated_at triggers
CREATE TRIGGER update_auth_rate_limits_updated_at 
    BEFORE UPDATE ON auth_rate_limits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_account_lockouts_updated_at 
    BEFORE UPDATE ON account_lockouts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_totp_updated_at 
    BEFORE UPDATE ON user_totp
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to clean up old rate limit records
CREATE OR REPLACE FUNCTION cleanup_old_rate_limits()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_rate_limits 
    WHERE window_start < CURRENT_TIMESTAMP - INTERVAL '1 hour'
    AND (blocked_until IS NULL OR blocked_until < CURRENT_TIMESTAMP);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old audit logs (keep last 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth_audit_log 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMIT;