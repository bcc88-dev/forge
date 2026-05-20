-- Forge Supabase Schema v1
-- Run this in the Supabase SQL Editor (https://supabase.com/dashboard/project/bzfgbkhkjxspvonwxtku/sql/new)

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- MEMORY TABLE (core feature - persistent agent memory)
-- ============================================================================
CREATE TABLE IF NOT EXISTS forge_memory (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    project_path TEXT DEFAULT '',
    embedding vector(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS forge_memory_user_idx ON forge_memory(user_id);
CREATE INDEX IF NOT EXISTS forge_memory_key_idx ON forge_memory(key);
CREATE INDEX IF NOT EXISTS forge_memory_project_idx ON forge_memory(project_path);
CREATE UNIQUE INDEX IF NOT EXISTS forge_memory_unique ON forge_memory(user_id, project_path, key);
CREATE INDEX IF NOT EXISTS forge_memory_embedding_idx ON forge_memory USING hnsw(embedding vector_cosine_ops);

-- RLS: users only see their own memories
ALTER TABLE forge_memory ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS forge_memory_user_isolation ON forge_memory;
CREATE POLICY forge_memory_user_isolation ON forge_memory
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Vector search function
CREATE OR REPLACE FUNCTION match_forge_memory(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    user_id_filter uuid DEFAULT NULL,
    project_filter text DEFAULT ''
)
RETURNS TABLE(key text, value text, distance float, metadata JSONB) AS $$
BEGIN
    RETURN QUERY
    SELECT
        forge_memory.key,
        forge_memory.value,
        1 - (forge_memory.embedding <=> query_embedding) as distance,
        forge_memory.metadata
    FROM forge_memory
    WHERE forge_memory.embedding IS NOT NULL
    AND (user_id_filter IS NULL OR forge_memory.user_id = user_id_filter)
    AND (project_filter = '' OR forge_memory.project_path = project_filter)
    AND 1 - (forge_memory.embedding <=> query_embedding) > match_threshold
    ORDER BY forge_memory.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recent memories function
CREATE OR REPLACE FUNCTION get_recent_forge_memories(
    limit_count int DEFAULT 10,
    user_id_filter uuid DEFAULT NULL,
    project_filter text DEFAULT ''
)
RETURNS TABLE(key text, value text, created_at timestamp, metadata JSONB) AS $$
BEGIN
    RETURN QUERY
    SELECT forge_memory.key, forge_memory.value, forge_memory.created_at, forge_memory.metadata
    FROM forge_memory
    WHERE (user_id_filter IS NULL OR forge_memory.user_id = user_id_filter)
    AND (project_filter = '' OR forge_memory.project_path = project_filter)
    ORDER BY forge_memory.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- SESSIONS TABLE (chat history persistence)
-- ============================================================================
CREATE TABLE IF NOT EXISTS forge_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    message_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE forge_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS forge_sessions_user_isolation ON forge_sessions;
CREATE POLICY forge_sessions_user_isolation ON forge_sessions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ============================================================================
-- MESSAGES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS forge_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES forge_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE forge_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS forge_messages_session_isolation ON forge_messages;
CREATE POLICY forge_messages_session_isolation ON forge_messages
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM forge_sessions
            WHERE forge_sessions.id = forge_messages.session_id
            AND forge_sessions.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM forge_sessions
            WHERE forge_sessions.id = forge_messages.session_id
            AND forge_sessions.user_id = auth.uid()
        )
    );

-- ============================================================================
-- LICENSES TABLE (admin only)
-- ============================================================================
CREATE TABLE IF NOT EXISTS forge_licenses (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    license_key TEXT UNIQUE NOT NULL,
    tier TEXT NOT NULL DEFAULT 'individual',
    status TEXT NOT NULL DEFAULT 'active',
    stripe_subscription_id TEXT,
    stripe_customer_id TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE forge_licenses ENABLE ROW LEVEL SECURITY;

-- Only service_role can manage licenses
DROP POLICY IF EXISTS forge_licenses_admin ON forge_licenses;
CREATE POLICY forge_licenses_admin ON forge_licenses
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
