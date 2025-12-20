-- ============================================
-- PostgreSQL Database Setup for Document Embeddings
-- ============================================

-- ============================================
-- Option 1: WITH pgvector extension (RECOMMENDED)
-- ============================================
-- Requires: PostgreSQL 11+ with pgvector installed
-- Installation guide: https://github.com/pgvector/pgvector

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table with vector column
-- Note: Adjust vector dimension (768) based on your embedding model
-- text-embedding-nomic-embed-text-v1.5 uses 768 dimensions
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(768),  -- Adjust dimension to match your model
    document_name TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast similarity search (optional, for semantic search)
-- Using ivfflat index with cosine distance
-- Adjust 'lists' parameter based on your dataset size (100 is good for < 1M vectors)
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create indexes for lookup operations
CREATE INDEX IF NOT EXISTS documents_doc_name_idx
ON documents(document_name);

CREATE INDEX IF NOT EXISTS documents_file_hash_idx
ON documents(file_hash);

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Table "documents" created successfully with pgvector support!';
    RAISE NOTICE 'You can now use the PostgreSQL backend with vector similarity search.';
END $$;


-- ============================================
-- Option 2: WITHOUT pgvector extension (FALLBACK)
-- ============================================
-- Use this if pgvector is not available
-- Uncomment the following lines and comment out Option 1 above

/*
-- Create table with array column instead of vector type
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding REAL[],  -- Array of floats instead of vector type
    document_name TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for lookup operations
CREATE INDEX IF NOT EXISTS documents_doc_name_idx
ON documents(document_name);

CREATE INDEX IF NOT EXISTS documents_file_hash_idx
ON documents(file_hash);

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Table "documents" created successfully without pgvector (using REAL[] arrays)!';
    RAISE NOTICE 'Note: Similarity search will be slower without pgvector extension.';
END $$;
*/


-- ============================================
-- Verify Setup
-- ============================================

-- Check if pgvector extension is installed
SELECT
    CASE
        WHEN EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')
        THEN 'pgvector extension is installed ✓'
        ELSE 'pgvector extension is NOT installed (using REAL[] arrays)'
    END as pgvector_status;

-- View table schema
\d documents

-- Count existing documents
SELECT COUNT(*) as total_documents FROM documents;

-- Sample query to verify structure (will return 0 rows if table is empty)
SELECT id, document_name, chunk_index, file_hash, processed_at
FROM documents
LIMIT 5;


-- ============================================
-- Useful Queries for Testing
-- ============================================

-- Query documents by name
-- SELECT * FROM documents WHERE document_name = 'your_file.pdf';

-- Count chunks per document
-- SELECT document_name, COUNT(*) as num_chunks
-- FROM documents
-- GROUP BY document_name
-- ORDER BY num_chunks DESC;

-- Find documents by hash (check for duplicates)
-- SELECT document_name, file_hash, COUNT(*) as occurrences
-- FROM documents
-- GROUP BY document_name, file_hash
-- ORDER BY occurrences DESC;

-- Delete all chunks for a specific document
-- DELETE FROM documents WHERE document_name = 'your_file.pdf';

-- Semantic search using pgvector (requires pgvector extension)
-- Replace [0.1, 0.2, ...] with your query embedding vector
-- SELECT content, document_name, chunk_index,
--        1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
-- FROM documents
-- ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
-- LIMIT 5;
