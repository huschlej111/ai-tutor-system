-- Ensure progress_records table exists (idempotent)
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
