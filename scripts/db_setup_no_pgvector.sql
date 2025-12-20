-- ============================================
-- PostgreSQL Setup WITHOUT pgvector extension
-- ============================================
-- Use this if pgvector is not yet installed
-- The Python code will automatically detect this and use REAL[] arrays

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
    RAISE NOTICE 'The system will automatically work with this setup.';
END $$;

-- Verify setup
SELECT COUNT(*) as total_documents FROM documents;
