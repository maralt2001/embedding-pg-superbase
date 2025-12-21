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

### CLI Usage

The project provides a comprehensive command-line interface via `cli.py` with three main commands:

**1. Embed Documents** (process and generate embeddings)
```bash
# Process a single document
python cli.py embed document.pdf

# Process multiple documents
python cli.py embed doc1.pdf doc2.docx doc3.txt

# Process all documents in a directory
python cli.py embed --directory ./documents

# Force re-processing (skip incremental update check)
python cli.py embed --force document.pdf

# Custom chunking settings
python cli.py embed --chunk-size 500 --strategy paragraph document.pdf
python cli.py embed --overlap 100 --strategy character document.pdf
```

**2. Search for Similar Chunks** (semantic search)
```bash
# Basic search
python cli.py search "What is Ansible?"

# Search with custom result limit
python cli.py search "configuration management" --limit 10

# Search in specific table
python cli.py search "deployment strategies" --table my_docs
```

**3. Show Document Status** (list processed documents)
```bash
# Show all processed documents
python cli.py status

# Show status for specific table
python cli.py status --table my_docs
```

**Global Options** (apply to all commands):
```bash
# Override storage backend
python cli.py --backend postgresql embed document.pdf
python cli.py --backend supabase search "query"

# Override table name
python cli.py --table custom_table embed document.pdf

# Custom LM Studio URL
python cli.py --lm-studio-url http://192.168.1.100:1234/v1 embed document.pdf

# Override database credentials (useful for CI/CD)
python cli.py --postgres-host localhost --postgres-db mydb embed document.pdf
```

**Getting Help**:
```bash
# General help
python cli.py --help

# Command-specific help
python cli.py embed --help
python cli.py search --help
python cli.py status --help
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

**cli.py**
- Command-line interface with argparse support
- Three main commands: `embed`, `search`, `status`
- Supports all configuration via CLI arguments or environment variables
- Batch processing support (multiple files or directory)
- Comprehensive help messages and examples

**main.py**
- Legacy entry point that loads environment variables and processes documents
- Configurable via environment variables for all major parameters
- Handles storage backend selection and initialization
- Handles skipped vs. processed document status
- Example usage with error handling
- Note: `cli.py` is recommended for new usage

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

### 5. Command-Line Interface
Comprehensive CLI with argparse support:
- **embed**: Process single/multiple documents or entire directories
- **search**: Semantic search across all processed documents
- **status**: View summary of all processed documents
- All settings configurable via CLI arguments or environment variables
- Batch processing with progress reporting

### 6. Semantic Search
Query your embedded documents using natural language:
- Cosine similarity search using embeddings
- Configurable result limits
- Returns relevance scores and content previews
- Works with both Supabase and PostgreSQL backends
- Optimized with pgvector when available
