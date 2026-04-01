-- ============================================================
-- Migration 002: Semantic memory with pgvector (Phase 3)
-- Requires: pgvector extension enabled in Supabase
-- ============================================================

-- -----------------------------------------------------------
-- 1. Enable pgvector extension
-- -----------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------
-- 2. Memory vectors table
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_vectors (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id),
    agent_role  TEXT,                    -- null = shared org-wide memory
    source_type TEXT NOT NULL,           -- "conversation", "document", "task_result"
    content     TEXT NOT NULL,
    embedding   vector(1536),           -- text-embedding-3-small (OpenAI)
    metadata    JSONB DEFAULT '{}',
    valid_to    TIMESTAMPTZ DEFAULT 'infinity',
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- -----------------------------------------------------------
-- 3. IVFFlat index for cosine similarity search
-- -----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_memory_embedding
    ON memory_vectors USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_memory_org ON memory_vectors(org_id);
CREATE INDEX IF NOT EXISTS idx_memory_agent ON memory_vectors(org_id, agent_role);

-- -----------------------------------------------------------
-- 4. RPC: semantic search function
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION search_memories(
    query_embedding vector(1536),
    p_org_id        UUID,
    p_agent_role    TEXT DEFAULT NULL,
    match_limit     INT DEFAULT 5,
    min_similarity  FLOAT DEFAULT 0.7
) RETURNS TABLE(id UUID, content TEXT, similarity FLOAT) AS $$
    SELECT id, content, 1 - (embedding <=> query_embedding) AS similarity
      FROM memory_vectors
     WHERE org_id = p_org_id
       AND (p_agent_role IS NULL OR agent_role = p_agent_role)
       AND valid_to > now()
       AND 1 - (embedding <=> query_embedding) >= min_similarity
     ORDER BY embedding <=> query_embedding
     LIMIT match_limit;
$$ LANGUAGE sql;

-- -----------------------------------------------------------
-- 5. Row Level Security
-- -----------------------------------------------------------
ALTER TABLE memory_vectors ENABLE ROW LEVEL SECURITY;
CREATE POLICY memory_vectors_org_access ON memory_vectors
    FOR ALL
    USING (org_id::text = current_org_id());
