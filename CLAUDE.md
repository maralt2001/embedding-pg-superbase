# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a document embedding pipeline that:
1. Reads documents (PDF, DOCX, TXT)
2. Chunks text with configurable strategies (character-based or paragraph-based)
3. Generates embeddings via LM Studio (local embedding server)
4. Stores chunks and embeddings in your choice of storage backend (Supabase or local PostgreSQL)
5. Implements incremental updates to avoid reprocessing unchanged documents

## Environment Setup

### Storage Backend Configuration

The system supports two storage backends: **Supabase** (cloud) and **PostgreSQL** (local). Configure one in your `.env` file:

**Option 1: Supabase Backend**
```bash
STORAGE_BACKEND=supabase  # Optional, auto-detected if SUPABASE_URL is set
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

**Option 2: PostgreSQL Backend**
```bash
STORAGE_BACKEND=postgresql  # Optional, auto-detected if POSTGRES_HOST is set
POSTGRES_HOST=localhost
POSTGRES_PORT=5432  # Optional, defaults to 5432
POSTGRES_DB=embeddings_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_SSLMODE=prefer  # Optional: disable, allow, prefer, require
```

**Common Configuration** (applies to both backends)
```bash
LM_STUDIO_URL=http://localhost:1234/v1  # Optional, defaults to this
CHUNK_SIZE=1000  # Optional
CHUNK_OVERLAP=200  # Optional (only used for character-based chunking)
TABLE_NAME=documents  # Optional
CHUNKING_STRATEGY=paragraph  # Optional: "character" or "paragraph" (default: "character")
SKIP_IF_EXISTS=true  # Optional: Skip unchanged documents (default: true)
```

**Backend Selection:**
- If `STORAGE_BACKEND` is set, that backend will be used
- If not set, the system auto-detects based on available credentials
- Existing `.env` files with only Supabase config continue to work unchanged

## Development Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### PostgreSQL Database Setup (if using PostgreSQL backend)

1. **Create the database:**
```bash
createdb embeddings_db
```

2. **Run the setup script:**
```bash
psql -d embeddings_db -f db_setup.sql
```

3. **Optional: Install pgvector extension (recommended for better performance)**

**macOS (with Homebrew):**
```bash
brew install pgvector
```

**Ubuntu/Debian:**
```bash
sudo apt install postgresql-server-dev-all
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**Then enable in your database:**
```bash
psql -d embeddings_db -c "CREATE EXTENSION vector;"
```

**Without pgvector:** The system automatically falls back to using `REAL[]` arrays. Similarity search will be slower but functional.

### Run the Pipeline
```bash
python main.py
```

## Architecture

### Core Components

**storage_backends.py**
- `StorageBackend`: Abstract base class defining storage interface
- `SupabaseBackend`: Implementation for Supabase cloud storage
- `PostgreSQLBackend`: Implementation for local PostgreSQL storage
  - Auto-detects pgvector extension availability
  - Falls back to `REAL[]` arrays if pgvector not available
- `create_storage_backend()`: Factory function for automatic backend selection

**DocumentEmbedder (document_embedder.py)**
- Main class orchestrating the embedding pipeline
- `read_document()`: Static method supporting PDF (PyPDF2), DOCX (python-docx), and TXT
- `chunk_text()`: Splits text using configurable strategies (character or paragraph-based)
- `_chunk_by_paragraph()`: Private method for paragraph-based chunking with intelligent splitting
- `calculate_file_hash()`: Computes SHA256 hash for change detection
- `get_embedding()`: Calls LM Studio API using model `text-embedding-nomic-embed-text-v1.5`
- `process_document()`: Full pipeline method with incremental update support
- Uses `StorageBackend` for all storage operations (backend-agnostic)

**main.py**
- Entry point that loads environment variables and processes documents
- Configurable via environment variables for all major parameters
- Handles storage backend selection and initialization
- Handles skipped vs. processed document status
- Example usage with error handling

### External Dependencies

**LM Studio**: Local embedding server expected at `LM_STUDIO_URL`
- Uses OpenAI-compatible `/embeddings` endpoint
- Model: `text-embedding-nomic-embed-text-v1.5`

**Storage Backends** (choose one):

**Supabase** (Cloud vector database)
- Uses official `supabase-py` client
- Cloud-hosted PostgreSQL with built-in pgvector
- Ideal for: Production deployments, team collaboration, managed infrastructure

**PostgreSQL** (Local vector database)
- Uses `psycopg2` driver
- Self-hosted PostgreSQL (optional pgvector extension)
- Ideal for: Local development, privacy-sensitive data, full control

**Common table schema** (both backends):
- `content` (text) - The chunk text
- `embedding` (vector or REAL[]) - The embedding vector
- `document_name` (text) - Name of the source document
- `chunk_index` (int) - Index of this chunk within the document
- `file_hash` (text) - SHA256 hash for change detection
- `processed_at` (timestamptz) - Timestamp when processed

### Data Flow

**With incremental updates enabled (default):**
```
Document File → calculate_file_hash() → storage.check_document_exists()
  ↓ (if unchanged)
  └→ Skip processing

  ↓ (if new or changed)
  └→ [if changed] storage.delete_document_chunks()
  └→ read_document() → chunk_text() →
     [for each chunk] → get_embedding() →
     [collect all with metadata] → storage.upload_chunks()
```

**With incremental updates disabled:**
```
Document File → read_document() → chunk_text() →
  [for each chunk] → get_embedding() →
  [collect all with metadata] → storage.upload_chunks()
```

## Key Implementation Details

### Chunking Strategies
- **Character-based**: Fixed-size chunks with configurable overlap to preserve context across boundaries
- **Paragraph-based**: Respects paragraph boundaries (\n\n), combines paragraphs up to max size, intelligently splits large paragraphs by sentences

### Incremental Updates
- SHA256 file hashing for change detection
- Automatic skip of unchanged documents (saves API calls and processing time)
- Automatic cleanup and re-upload when documents change
- Metadata tracking with file_hash and processed_at timestamps

### Processing
- Embeddings are generated synchronously (one API call per chunk)
- Storage upload is done in a single batch insert operation
- File type detection uses Path.suffix

### Storage Backend Architecture
- **Adapter pattern**: Abstract `StorageBackend` interface with multiple implementations
- **Automatic selection**: Factory function chooses backend based on environment variables
- **Backward compatible**: Existing Supabase configurations work without changes
- **PostgreSQL specifics**:
  - Auto-detects pgvector extension availability
  - Falls back to `REAL[]` arrays if pgvector not installed
  - Uses parameterized queries for SQL injection prevention
  - Single synchronous connection per DocumentEmbedder instance

## Features

### 1. Flexible Storage Backends
Choose between Supabase (cloud) or PostgreSQL (local):
- **Supabase**: Managed infrastructure, zero database setup, built-in pgvector
- **PostgreSQL**: Full control, local development, privacy-sensitive data
- Both use identical table schema for easy migration

### 2. Multiple Chunking Strategies
Set `CHUNKING_STRATEGY=paragraph` for natural document structure preservation, or `character` for consistent chunk sizes with overlap.

### 3. Incremental Updates
Set `SKIP_IF_EXISTS=true` to automatically skip unchanged documents. The system:
- Calculates file hash on each run
- Compares with stored hash in database
- Skips processing if unchanged (fast)
- Auto-updates if file changed (removes old chunks, adds new ones)

### 4. Metadata Tracking
All chunks include:
- Document name and chunk index
- File hash for change detection
- Processing timestamp for audit trail
