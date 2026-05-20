CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS nyx_memory (
    id SERIAL PRIMARY KEY,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    project_path TEXT DEFAULT '',
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS nyx_memory_key_idx ON nyx_memory(key);
CREATE INDEX IF NOT EXISTS nyx_memory_project_idx ON nyx_memory(project_path);
CREATE UNIQUE INDEX IF NOT EXISTS nyx_memory_unique ON nyx_memory(project_path, key);
CREATE INDEX IF NOT EXISTS nyx_memory_embedding_idx ON nyx_memory USING hnsw(embedding vector_cosine_ops);

ALTER TABLE nyx_memory ENABLE ROW LEVEL SECURITY;

-- Allow anon key access (valid JWT required — rejects bad keys)
-- Uses auth.role() = 'anon' so PostgREST validates the JWT signature
DROP POLICY IF EXISTS public_all ON nyx_memory;
CREATE POLICY anon_access ON nyx_memory FOR ALL USING (auth.role() = 'anon') WITH CHECK (auth.role() = 'anon');

CREATE OR REPLACE FUNCTION match_memory(
    query_embedding vector,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    project_filter text DEFAULT ''
)
RETURNS TABLE(key text, value text, distance float) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        nyx_memory.key,
        nyx_memory.value,
        1 - (nyx_memory.embedding <=> query_embedding) as distance
    FROM nyx_memory
    WHERE nyx_memory.embedding IS NOT NULL
    AND (project_filter = '' OR nyx_memory.project_path = project_filter)
    AND 1 - (nyx_memory.embedding <=> query_embedding) > match_threshold
    ORDER BY nyx_memory.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_recent_memories(
    limit_count int DEFAULT 10,
    project_filter text DEFAULT ''
)
RETURNS TABLE(key text, value text, created_at timestamp) AS $$
BEGIN
    RETURN QUERY
    SELECT nyx_memory.key, nyx_memory.value, nyx_memory.created_at
    FROM nyx_memory
    WHERE project_filter = '' OR nyx_memory.project_path = project_filter
    ORDER BY nyx_memory.created_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GITHUB MEMORY TABLES (for GitHub integration as memory layer)
-- ============================================================================

CREATE TABLE IF NOT EXISTS github_repos (
    id SERIAL PRIMARY KEY,
    repo_name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    description TEXT,
    stars INTEGER DEFAULT 0,
    language TEXT,
    topics TEXT[],
    url TEXT,
    synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(full_name)
);

CREATE INDEX IF NOT EXISTS github_repos_name_idx ON github_repos(repo_name);
CREATE INDEX IF NOT EXISTS github_repos_full_name_idx ON github_repos(full_name);

CREATE TABLE IF NOT EXISTS github_issues (
    id SERIAL PRIMARY KEY,
    repo TEXT NOT NULL,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    state TEXT,
    labels TEXT[],
    author TEXT,
    url TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(repo, number)
);

CREATE INDEX IF NOT EXISTS github_issues_repo_idx ON github_issues(repo);
CREATE INDEX IF NOT EXISTS github_issues_number_idx ON github_issues(number);

CREATE TABLE IF NOT EXISTS github_prs (
    id SERIAL PRIMARY KEY,
    repo TEXT NOT NULL,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    state TEXT,
    labels TEXT[],
    author TEXT,
    url TEXT,
    merged_at TIMESTAMP,
    created_at TIMESTAMP,
    synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(repo, number)
);

CREATE INDEX IF NOT EXISTS github_prs_repo_idx ON github_prs(repo);
CREATE INDEX IF NOT EXISTS github_prs_number_idx ON github_prs(number);

-- RLS for GitHub tables
ALTER TABLE github_repos ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_prs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS public_all_github ON github_repos;
DROP POLICY IF EXISTS public_all_github_issues ON github_issues;
DROP POLICY IF EXISTS public_all_github_prs ON github_prs;
CREATE POLICY anon_access_github ON github_repos FOR ALL USING (auth.role() = 'anon') WITH CHECK (auth.role() = 'anon');
CREATE POLICY anon_access_github_issues ON github_issues FOR ALL USING (auth.role() = 'anon') WITH CHECK (auth.role() = 'anon');
CREATE POLICY anon_access_github_prs ON github_prs FOR ALL USING (auth.role() = 'anon') WITH CHECK (auth.role() = 'anon');