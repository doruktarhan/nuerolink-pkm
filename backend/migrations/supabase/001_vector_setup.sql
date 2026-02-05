-- NeuroLink Phase 2: Supabase Vector Setup
-- Run this in the Supabase SQL Editor

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- Create embeddings table
CREATE TABLE item_embeddings (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  neurolink_item_id BIGINT NOT NULL,
  source_url TEXT NOT NULL,
  content_type TEXT,
  content_preview TEXT,  -- 500 chars max
  embedding extensions.vector(1536),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Unique constraint on neurolink_item_id
CREATE UNIQUE INDEX item_embeddings_neurolink_item_id_unique
  ON item_embeddings (neurolink_item_id);

-- HNSW index for fast similarity search
CREATE INDEX item_embeddings_embedding_idx
  ON item_embeddings USING hnsw (embedding vector_cosine_ops);

-- Similarity search function with content_type and date filters
CREATE OR REPLACE FUNCTION match_items (
  query_embedding extensions.vector(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 10,
  filter_content_type TEXT DEFAULT NULL,
  filter_after TIMESTAMP WITH TIME ZONE DEFAULT NULL,
  filter_before TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS TABLE (
  id BIGINT,
  neurolink_item_id BIGINT,
  source_url TEXT,
  content_type TEXT,
  content_preview TEXT,
  similarity FLOAT,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE sql STABLE
AS $$
  SELECT
    item_embeddings.id,
    item_embeddings.neurolink_item_id,
    item_embeddings.source_url,
    item_embeddings.content_type,
    item_embeddings.content_preview,
    1 - (item_embeddings.embedding <=> query_embedding) AS similarity,
    item_embeddings.created_at
  FROM item_embeddings
  WHERE item_embeddings.embedding IS NOT NULL
    AND 1 - (item_embeddings.embedding <=> query_embedding) > match_threshold
    AND (filter_content_type IS NULL OR item_embeddings.content_type = filter_content_type)
    AND (filter_after IS NULL OR item_embeddings.created_at >= filter_after)
    AND (filter_before IS NULL OR item_embeddings.created_at <= filter_before)
  ORDER BY item_embeddings.embedding <=> query_embedding ASC
  LIMIT LEAST(match_count, 100);
$$;
