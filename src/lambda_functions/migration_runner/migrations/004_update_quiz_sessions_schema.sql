-- Migration: Update quiz_sessions table schema
-- Adds missing columns for quiz engine compatibility
-- Date: 2026-02-19

-- Add missing columns to quiz_sessions
ALTER TABLE quiz_sessions 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
ADD COLUMN IF NOT EXISTS current_term_index INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_questions INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS correct_answers INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS session_data JSONB DEFAULT '{}';

-- Rename session_state to match if it exists (keep both for now)
-- session_state will be deprecated in favor of session_data

-- Create indexes for quiz operations
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user ON quiz_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_domain ON quiz_sessions(domain_id);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_status ON quiz_sessions(status);
CREATE INDEX IF NOT EXISTS idx_quiz_sessions_user_status ON quiz_sessions(user_id, status);
