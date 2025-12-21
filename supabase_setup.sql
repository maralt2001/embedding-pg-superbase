-- Supabase Setup SQL
-- Run this in your Supabase SQL Editor to enable vector similarity search

-- Step 1: Enable pgvector extension (if not already enabled)
-- Go to Database > Extensions in Supabase dashboard and enable "vector"
-- Or run: CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create the documents table
CREATE TABLE IF NOT EXISTS documents (
  id BIGSERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  embedding vector(768),
  document_name TEXT NOT NULL,
  chunk_index INT NOT NULL,
  file_hash TEXT,
  processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: Create index for faster similarity search
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Step 4: Create the match_documents function for similarity search
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(768),
  match_threshold float DEFAULT 0.0,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  content text,
  document_name text,
  chunk_index int,
  similarity float,
  file_hash text,
  processed_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    documents.id,
    documents.content,
    documents.document_name,
    documents.chunk_index,
    1 - (documents.embedding <=> query_embedding) as similarity,
    documents.file_hash,
    documents.processed_at
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY documents.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Alternative: If you need to search in different tables, create separate functions
-- For example, for a table called "my_docs":
--
-- CREATE TABLE IF NOT EXISTS my_docs (
--   id BIGSERIAL PRIMARY KEY,
--   content TEXT NOT NULL,
--   embedding vector(768),
--   document_name TEXT NOT NULL,
--   chunk_index INT NOT NULL,
--   file_hash TEXT,
--   processed_at TIMESTAMPTZ DEFAULT NOW()
-- );
--
-- CREATE INDEX IF NOT EXISTS my_docs_embedding_idx ON my_docs
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);
--
-- CREATE OR REPLACE FUNCTION match_my_docs(
--   query_embedding vector(768),
--   match_threshold float DEFAULT 0.0,
--   match_count int DEFAULT 5
-- )
-- RETURNS TABLE (
--   id bigint,
--   content text,
--   document_name text,
--   chunk_index int,
--   similarity float,
--   file_hash text,
--   processed_at timestamptz
-- )
-- LANGUAGE plpgsql
-- AS $$
-- BEGIN
--   RETURN QUERY
--   SELECT
--     my_docs.id,
--     my_docs.content,
--     my_docs.document_name,
--     my_docs.chunk_index,
--     1 - (my_docs.embedding <=> query_embedding) as similarity,
--     my_docs.file_hash,
--     my_docs.processed_at
--   FROM my_docs
--   WHERE 1 - (my_docs.embedding <=> query_embedding) > match_threshold
--   ORDER BY my_docs.embedding <=> query_embedding
--   LIMIT match_count;
-- END;
-- $$;
