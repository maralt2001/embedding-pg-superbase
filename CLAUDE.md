# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a document embedding pipeline that:
1. Reads documents (PDF, DOCX, TXT)
2. Chunks text with configurable strategies (character-based, paragraph-based, or semantic)
3. Generates embeddings via LM Studio (local embedding server)
4. Stores chunks and embeddings in PostgreSQL database
5. Implements incremental updates to avoid reprocessing unchanged documents
6. Provides both CLI and web interface for easy interaction

## Environment Setup

### PostgreSQL Backend Configuration

Configure PostgreSQL connection in your `.env` file:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432  # Optional, defaults to 5432
POSTGRES_DB=embeddings_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_SSLMODE=prefer  # Optional: disable, allow, prefer, require
```

**Common Configuration**
```bash
LM_STUDIO_URL=http://localhost:1234/v1  # Optional, defaults to this
CHUNK_SIZE=1000  # Optional
CHUNK_OVERLAP=200  # Optional (only used for character-based chunking)
TABLE_NAME=documents  # Optional
CHUNKING_STRATEGY=paragraph  # Optional: "character", "paragraph", or "semantic" (default: "character")
SEMANTIC_SIMILARITY_THRESHOLD=0.75  # Optional: For semantic chunking (0.0-1.0, default: 0.75)
SKIP_IF_EXISTS=true  # Optional: Skip unchanged documents (default: true)
EMBEDDING_MAX_WORKERS=4  # Optional: Max parallel workers for batch embedding (default: 4)
```

## Development Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### CLI Usage

The project provides a comprehensive command-line interface via `scripts/cli.py` with four main commands:

**1. Embed Documents** (process and generate embeddings)
```bash
# Process a single document
python scripts/cli.py embed document.pdf

# Process multiple documents
python scripts/cli.py embed doc1.pdf doc2.docx doc3.txt

# Process all documents in a directory
python scripts/cli.py embed --directory ./documents

# Force re-processing (skip incremental update check)
python scripts/cli.py embed --force document.pdf

# Custom chunking settings
python scripts/cli.py embed --chunk-size 500 --strategy paragraph document.pdf
python scripts/cli.py embed --overlap 100 --strategy character document.pdf

# Semantic chunking with embedding similarity
python scripts/cli.py embed --strategy semantic document.pdf
python scripts/cli.py embed --strategy semantic --similarity-threshold 0.8 document.pdf
```

**2. Search for Similar Chunks** (semantic search)
```bash
# Basic search
python scripts/cli.py search "What is Ansible?"

# Search with custom result limit
python scripts/cli.py search "configuration management" --limit 10

# Filter by document name
python scripts/cli.py search "deployment strategies" --document my_doc.pdf

# Filter by minimum similarity score
python scripts/cli.py search "What is Docker?" --min-score 0.7

# Combine filters
python scripts/cli.py search "kubernetes" --document guide.pdf --min-score 0.8 --limit 5

# Search in specific table
python scripts/cli.py search "deployment strategies" --table my_docs
```

**3. Show Document Status** (list processed documents)
```bash
# Show all processed documents
python scripts/cli.py status

# Show status for specific table
python scripts/cli.py status --table my_docs
```

**4. Delete Documents** (remove a document and all its chunks)
```bash
# Delete a document (with confirmation prompt)
python scripts/cli.py delete document.pdf

# Delete without confirmation
python scripts/cli.py delete --force document.pdf

# Delete from specific table
python scripts/cli.py --table my_docs delete document.pdf
```

**Global Options** (apply to all commands):
```bash
# Override database credentials (useful for CI/CD)
python scripts/cli.py --postgres-host localhost --postgres-db mydb embed document.pdf

# Override table name
python scripts/cli.py --table custom_table embed document.pdf

# Custom LM Studio URL
python scripts/cli.py --lm-studio-url http://192.168.1.100:1234/v1 embed document.pdf

# Override database credentials (useful for CI/CD)
python scripts/cli.py --postgres-host localhost --postgres-db mydb embed document.pdf
```

**Getting Help**:
```bash
# General help
python scripts/cli.py --help

# Command-specific help
python scripts/cli.py embed --help
python scripts/cli.py search --help
python scripts/cli.py status --help
```

### Web Interface Usage

The project includes a modern web-based interface built with FastAPI and vanilla JavaScript. This provides a user-friendly GUI alternative to the CLI.

**Start the Web Server:**
```bash
# Development mode (default - localhost only, auto-reload enabled)
python run.py

# Production mode (network accessible, multiple workers, no reload)
ENVIRONMENT=production python run.py

# Or set in .env file:
# ENVIRONMENT=production
# then just run:
python run.py

# Custom port (works in both environments)
WEB_PORT=8080 python run.py

# Override defaults with environment variables
WEB_HOST=0.0.0.0 WEB_PORT=8080 python run.py
```

**Environment Modes:**
- **Development** (default): Runs on `127.0.0.1:8000`, auto-reload enabled, debug logging, single worker
- **Production**: Runs on `0.0.0.0:8000`, auto-reload disabled, info logging, 4 workers (configurable via `WEB_WORKERS`)

**Direct uvicorn usage** (alternative to run.py):
```bash
# Development
uvicorn backend.api.app:app --reload

# Production
uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

**Access the Interface:**
Open your browser and navigate to `http://localhost:8000`

**Web Interface Features:**

1. **Upload Tab** - Document Processing
   - Drag & drop or click to browse for files (PDF, DOCX, TXT)
   - Real-time progress tracking with visual progress bar
   - Automatic duplicate detection (respects `SKIP_IF_EXISTS` setting)
   - Shows processing stages: reading → chunking → embedding → uploading
   - Maximum file size: 50MB
   - Display of processing results (chunks created, processing time)

2. **Search Tab** - Semantic Search
   - Natural language query input
   - Configurable result limit (5, 10, or 20 results)
   - Advanced filtering options:
     - Filter by specific document
     - Filter by minimum similarity score (0.0-1.0)
   - Results displayed with similarity scores (percentage match)
   - Document name and chunk index for each result
   - Content preview with expandable text
   - Helpful hints when no results found with filters active

3. **Documents Tab** - Document Management
   - List of all processed documents
   - Shows chunk count and processing timestamp for each document
   - Delete functionality with confirmation dialog
   - Refresh button to reload document list

4. **Settings Tab** - Configuration Display
   - Read-only display of settings: Backend type, LM Studio URL, table name, chunk size, chunking strategy, etc.
   - Note: Configuration changes must be made via `.env` file (requires server restart)

**Technical Details:**
- Uses same `.env` configuration as CLI
- Uses PostgreSQL as storage backend
- Background task processing (non-blocking uploads)
- In-memory task store with automatic cleanup (1 hour retention)
- Progress polling every 1.5 seconds
- Responsive design (mobile-friendly)
- No build step required (vanilla JavaScript)

**API Endpoints:**
The web interface exposes the following REST API endpoints:
- `POST /api/documents/upload` - Upload and process document
- `GET /api/tasks/{task_id}` - Get task status/progress
- `GET /api/documents` - List all documents
- `DELETE /api/documents/{name}` - Delete document
- `GET /api/search?query=...&limit=5` - Semantic search
- `GET /api/config` - Get current configuration

**Environment Variables for Web Interface:**
```bash
# Environment mode (development or production)
ENVIRONMENT=development  # Optional: "development" (default) or "production"

# Server configuration
WEB_HOST=127.0.0.1  # Optional: Override default host (auto-configured based on ENVIRONMENT)
WEB_PORT=8000  # Optional: Override default port
WEB_WORKERS=4  # Optional: Number of worker processes in production (default: 4, ignored in development)
WEB_RELOAD=true  # Optional: Override auto-reload setting (auto-configured based on ENVIRONMENT)
```

**Environment-specific defaults:**
- **Development mode** (`ENVIRONMENT=development` or not set):
  - Host: `127.0.0.1` (localhost only)
  - Reload: `true` (auto-reload on code changes)
  - Workers: `1` (single process)
  - Log level: `debug`

- **Production mode** (`ENVIRONMENT=production`):
  - Host: `0.0.0.0` (accessible from network)
  - Reload: `false` (no auto-reload)
  - Workers: `4` (multi-process for better performance)
  - Log level: `info`

All other configuration uses the same environment variables as the CLI (see Common Configuration section above).

### PostgreSQL Database Setup

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

### Run the Legacy Pipeline Script
```bash
python scripts/main.py
```

**Note:** For new usage, the CLI (`python scripts/cli.py`) or web interface (`python run.py`) is recommended.

## Docker Deployment

The application includes production-ready Docker support with multi-stage builds, optimized for minimal image size and maximum security.

### Docker Files

- **Dockerfile**: Multi-stage build (builder + runtime) with Python 3.11-slim
- **.dockerignore**: Excludes unnecessary files from build context (~40% faster builds)
- **docker-compose.yml**: Easy deployment with configuration examples

### Quick Start with Docker Compose (Recommended)

**1. Configure your environment** in `docker-compose.yml`:
```yaml
environment:
  # Storage Backend
  - STORAGE_BACKEND=postgresql
  - POSTGRES_HOST=your-postgres-host  # Your remote PostgreSQL server
  - POSTGRES_DB=embeddings_db
  - POSTGRES_USER=postgres
  - POSTGRES_PASSWORD=your-password

  # LM Studio
  - LM_STUDIO_URL=http://host.docker.internal:1234/v1  # Mac/Windows
  # - LM_STUDIO_URL=http://172.17.0.1:1234/v1  # Linux

  # Chunking
  - CHUNKING_STRATEGY=semantic  # character, paragraph, or semantic
```

**2. Start the application:**
```bash
docker-compose up -d
```

**3. Access the web interface:**
```
http://localhost:8000
```

**4. View logs:**
```bash
docker-compose logs -f
```

**5. Stop the application:**
```bash
docker-compose down
```

### Manual Docker Build & Run

**Build the image:**
```bash
docker build -t embedding-pipeline:latest .
```

**Run with PostgreSQL:**
```bash
docker run -d \
  -p 8000:8000 \
  -v ./uploads:/app/uploads \
  -e STORAGE_BACKEND=postgresql \
  -e POSTGRES_HOST=your-host \
  -e POSTGRES_DB=embeddings_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your-password \
  -e LM_STUDIO_URL=http://host.docker.internal:1234/v1 \
  --name embedding-pipeline \
  embedding-pipeline:latest
```

### Docker Image Specifications

**Image Details:**
- **Base Image**: `python:3.11-slim-bookworm`
- **Total Size**: ~484MB (optimized with multi-stage build)
- **Content Size**: ~105MB
- **Architecture**: Multi-stage (builder stage excluded from final image)
- **Build Time**: Initial ~60s, subsequent ~5-10s (layer caching)

**Security Features:**
- Runs as non-root user (`appuser`, UID/GID 1000)
- Minimal base image (slim variant)
- No secrets in image layers
- Read-only application code (only uploads/ writable)

**Production Configuration:**
- Environment: `ENVIRONMENT=production`
- Workers: 4 (configurable via `WEB_WORKERS`)
- Host: `0.0.0.0` (accessible from network)
- Port: `8000`
- Health Check: Enabled (checks `/api/config` every 30s)

**Volume Mounts:**
- `/app/uploads` - For persistent file storage across container restarts

### Configuration Notes

**LM Studio URL Configuration:**
- **Mac/Windows**: Use `http://host.docker.internal:1234/v1` to access LM Studio on host machine
- **Linux**: Use `http://172.17.0.1:1234/v1` or your actual host IP address
- **Another container**: Use the container name, e.g., `http://lm-studio:1234/v1`

**Storage Backend Options:**
1. **Remote PostgreSQL** (recommended for production):
   ```yaml
   - POSTGRES_HOST=your-database-server.com
   - POSTGRES_DB=embeddings_db
   - POSTGRES_USER=postgres
   - POSTGRES_PASSWORD=your-secure-password
   ```

2. **Local PostgreSQL** (for testing):
   - Uncomment the `postgres` service in `docker-compose.yml`
   - Uncomment the `postgres_data` volume
   - Set `POSTGRES_HOST=postgres` (uses Docker service name)

### Common Docker Commands

```bash
# Check container status
docker ps
docker-compose ps

# View logs (live)
docker logs -f embedding-pipeline
docker-compose logs -f

# Restart container
docker restart embedding-pipeline
docker-compose restart

# Stop and remove container
docker rm -f embedding-pipeline
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Access container shell (debugging)
docker exec -it embedding-pipeline /bin/bash

# Check image size
docker images embedding-pipeline

# Inspect container
docker inspect embedding-pipeline
```

### Dockerfile Structure

**Stage 1: Builder** (dependencies compilation)
```dockerfile
FROM python:3.11-slim-bookworm AS builder
- Install build-essential (gcc, make, etc.)
- Create virtual environment at /opt/venv
- Copy requirements.txt
- Install all Python dependencies
```

**Stage 2: Runtime** (minimal production image)
```dockerfile
FROM python:3.11-slim-bookworm
- Copy virtual environment from builder (no build tools)
- Create non-root user (appuser)
- Copy application code (backend/, frontend/, scripts/, run.py)
- Fix file permissions (chmod a+rX)
- Create uploads/ directory
- Set environment variables
- Configure health check
- Run as appuser
```

### Troubleshooting

**Container fails to start - Permission denied:**
- Fixed in current Dockerfile with `chmod -R a+rX /app`
- Rebuild image if using older version

**Can't connect to PostgreSQL:**
- Verify `POSTGRES_HOST` is accessible from container
- Check firewall rules allow port 5432
- Test connectivity: `docker-compose exec embedding-pipeline ping your-postgres-host`
- Verify credentials are correct

**Can't connect to LM Studio:**
- Ensure LM Studio is running with API server enabled (default port 1234)
- Mac/Windows: Use `host.docker.internal` to access host machine
- Linux: Use `172.17.0.1` or your host's actual IP
- Test: `docker-compose exec embedding-pipeline curl http://host.docker.internal:1234/v1/models`
- Check LM Studio logs for incoming requests

**Health check failing:**
- Wait 40 seconds (health check start period)
- Check logs: `docker-compose logs embedding-pipeline`
- Verify database connection is successful
- Ensure all environment variables are set correctly

**Permission errors with uploads/ directory:**
- Container runs as `appuser` (UID 1000)
- On host: `chown -R 1000:1000 uploads/` or `chmod 777 uploads/`

**Slow build times:**
- First build takes ~60 seconds (downloads base image + installs dependencies)
- Subsequent builds use layer caching (~5-10 seconds)
- Ensure `.dockerignore` is present to exclude unnecessary files

### Production Deployment Checklist

Before deploying to production:

- [ ] Update environment variables in `docker-compose.yml` with real credentials
- [ ] Change default PostgreSQL password
- [ ] Configure remote PostgreSQL backend
- [ ] Set `LM_STUDIO_URL` to accessible LM Studio instance
- [ ] Set up persistent volume mount for `/app/uploads`
- [ ] Configure reverse proxy (nginx/Traefik) for HTTPS
- [ ] Set up monitoring and log aggregation
- [ ] Configure resource limits (memory, CPU)
- [ ] Test health check endpoint
- [ ] Set up backup strategy for uploads/ directory
- [ ] Review security settings (firewall, network policies)
- [ ] Test with actual documents before production use

### Environment Variables Reference

All environment variables that can be configured:

```bash
# Web Server
ENVIRONMENT=production           # development or production
WEB_HOST=0.0.0.0                # Auto-configured based on ENVIRONMENT
WEB_PORT=8000                   # Default: 8000
WEB_WORKERS=4                   # Production default: 4
WEB_RELOAD=false                # Auto-configured based on ENVIRONMENT

# Storage Backend
POSTGRES_HOST=localhost         # Required
POSTGRES_PORT=5432              # Optional, default: 5432
POSTGRES_DB=embeddings_db       # Required
POSTGRES_USER=postgres          # Required
POSTGRES_PASSWORD=secret        # Required
POSTGRES_SSLMODE=prefer         # Optional: disable, allow, prefer, require

# LM Studio
LM_STUDIO_URL=http://localhost:1234/v1  # Required

# Embedding Model Configuration
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5  # Default model (768-dim)
# Alternative: text-embedding-qwen3-embedding-0.6b (1024-dim)

# Chunking Configuration
CHUNK_SIZE=1000                 # Default: 1000
CHUNK_OVERLAP=200               # Default: 200 (character strategy only)
CHUNKING_STRATEGY=paragraph     # character, paragraph, or semantic
SEMANTIC_SIMILARITY_THRESHOLD=0.75  # For semantic chunking (0.0-1.0, try 0.85 for stricter grouping)
TABLE_NAME=documents            # Default: documents
SKIP_IF_EXISTS=true            # Default: true

# Performance Configuration
EMBEDDING_MAX_WORKERS=4         # Default: 4 - Max parallel workers for batch embedding requests
```

## Architecture

### Core Components

**backend/storage/backends.py**
- `StorageBackend`: Abstract base class defining storage interface
- `PostgreSQLBackend`: Implementation for PostgreSQL storage
  - Auto-detects pgvector extension availability
  - Falls back to `REAL[]` arrays if pgvector not available
- `create_storage_backend()`: Factory function for creating PostgreSQL backend

**backend/services/embedder.py** (DocumentEmbedder)
- Main class orchestrating the embedding pipeline
- Configurable embedding model via `EMBEDDING_MODEL` environment variable
- `read_document()`: Static method supporting PDF (pymupdf), DOCX (python-docx), and TXT
- `chunk_text()`: Splits text using configurable strategies (character, paragraph, or semantic-based)
- `_chunk_by_paragraph()`: Private method for paragraph-based chunking with intelligent splitting
- `_chunk_by_semantic()`: Instance method for semantic chunking using embedding similarity
- `_split_into_sentences()`: Static helper to split text into sentences (handles abbreviations)
- `_calculate_cosine_similarity()`: Static helper to calculate similarity between embedding vectors
- `calculate_file_hash()`: Computes SHA256 hash for change detection
- `get_embedding()`: Calls LM Studio API using model `text-embedding-nomic-embed-text-v1.5`
- `process_document()`: Full pipeline method with incremental update support and progress callbacks
- Uses `StorageBackend` for all storage operations (backend-agnostic)

**scripts/cli.py**
- Command-line interface with argparse support
- Four main commands: `embed`, `search`, `status`, `delete`
- Supports all configuration via CLI arguments or environment variables
- Batch processing support (multiple files or directory)
- Comprehensive help messages and examples

**backend/api/app.py** (FastAPI application)
- FastAPI web application providing REST API and web interface
- API endpoints for upload, search, status, delete operations
- Dynamic backend switching endpoint (PUT /api/config)
- Background task processing for document uploads
- In-memory task store for progress tracking
- CORS middleware for development
- Static file serving for frontend
- Automatic cleanup of old tasks and uploaded files

**backend/services/web_service.py** (WebEmbeddingService)
- Service layer wrapper around DocumentEmbedder for web interface
- `WebEmbeddingService`: Provides progress tracking with callbacks
- Updates task store at each processing stage
- Handles file cleanup after processing
- Maps progress stages: reading → chunking → embedding → uploading

**frontend/static/** (Frontend assets)
- `index.html`: Tab-based UI (Upload, Search, Documents, Settings)
- `style.css`: Responsive design with gradient theme
- `app.js`: Vanilla JavaScript for all UI interactions
  - File upload with drag & drop
  - Progress polling (1.5 second intervals)
  - Search and document management
  - Backend switching functionality
  - Tab switching and UI state management

**run.py**
- Entry point for starting the web server
- Supports development and production environments via `ENVIRONMENT` variable
- Auto-configures host, port, workers, reload, and logging based on environment
- Development: localhost only, auto-reload, debug logging, single worker
- Production: network accessible, no reload, info logging, multi-worker
- Delegates to uvicorn to run backend.api.app:app

**scripts/main.py**
- Legacy entry point that loads environment variables and processes documents
- Configurable via environment variables for all major parameters
- Handles storage backend selection and initialization
- Handles skipped vs. processed document status
- Example usage with error handling
- Note: `scripts/cli.py` or web interface (`run.py`) is recommended for new usage

### External Dependencies

**LM Studio**: Local embedding server expected at `LM_STUDIO_URL`
- Uses OpenAI-compatible `/embeddings` endpoint
- Configurable embedding model via `EMBEDDING_MODEL` environment variable
- Default: `text-embedding-nomic-embed-text-v1.5` (768 dimensions)
- Alternative: `text-embedding-qwen3-embedding-0.6b` (1024 dimensions)
- **Important**: All documents must use the same embedding model (same dimensions)

**Storage Backend**:

**PostgreSQL**
- Uses `psycopg2` driver
- Self-hosted PostgreSQL (optional pgvector extension)
- Ideal for: Local development, privacy-sensitive data, full control

**Table schema**:
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
- **Character-based**: Fixed-size chunks with configurable overlap to preserve context across boundaries. Fast and predictable.
- **Paragraph-based**: Respects paragraph boundaries (\n\n), combines paragraphs up to max size, intelligently splits large paragraphs by sentences. Preserves document structure.
- **Semantic**: Groups sentences by embedding similarity to create semantically coherent chunks. Uses LM Studio API to generate embeddings for each sentence, then merges consecutive sentences when cosine similarity exceeds threshold (default: 0.75). Highest quality but slowest (requires N+1 API calls for N sentences). Best for documents where semantic coherence is critical for retrieval quality.

### Incremental Updates
- SHA256 file hashing for change detection
- Automatic skip of unchanged documents (saves API calls and processing time)
- Automatic cleanup and re-upload when documents change
- Metadata tracking with file_hash and processed_at timestamps

### Processing
- Embeddings are generated synchronously (one API call per chunk)
- Storage upload is done in a single batch insert operation
- File type detection uses Path.suffix

### PDF Text Extraction
- Uses **pymupdf (fitz)** for superior PDF text extraction
- Correctly preserves whitespace and formatting
- Previously used PyPDF2 (had issues with missing spaces between words)
- Significantly better text quality compared to PyPDF2

### Storage Backend Architecture
- **PostgreSQL backend**:
  - Auto-detects pgvector extension availability
  - Falls back to `REAL[]` arrays if pgvector not installed
  - Uses parameterized queries for SQL injection prevention
  - Single synchronous connection per DocumentEmbedder instance

## Features

### 1. PostgreSQL Storage Backend
- Full control over your data
- Optimized for local development and privacy-sensitive data
- Optional pgvector extension for optimized vector search
- Falls back to REAL[] arrays if pgvector not available

### 2. Multiple Chunking Strategies
Choose the chunking strategy that best fits your needs:
- **`character`**: Fast, fixed-size chunks with overlap (default)
- **`paragraph`**: Medium speed, respects paragraph boundaries
- **`semantic`**: Slow, highest quality - groups sentences by embedding similarity

Set via `CHUNKING_STRATEGY` environment variable or `--strategy` CLI argument. For semantic chunking, adjust `SEMANTIC_SIMILARITY_THRESHOLD` (0.0-1.0, default: 0.75) to control how strictly sentences must match to be grouped together.

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

### 5. Semantic Search with Advanced Filtering
Query your embedded documents using natural language:
- Cosine similarity search using embeddings
- Configurable result limits
- **Document name filtering**: Search within specific documents only
- **Score threshold filtering**: Set minimum similarity score (0.0-1.0)
- Returns relevance scores and content previews
- Optimized with pgvector when available
- Available in both CLI and web interface

### 6. Web Interface
Modern, user-friendly GUI built with FastAPI and vanilla JavaScript:
- **Upload Tab**: Drag & drop file upload with real-time progress tracking
- **Search Tab**: Natural language semantic search with configurable result limits
- **Documents Tab**: List and manage all processed documents
- **Settings Tab**: View system configuration (read-only)
- Background task processing (non-blocking uploads)
- Progress polling with visual feedback (reading → chunking → embedding → uploading)
- Responsive design (mobile-friendly)
- No build step required
- PostgreSQL storage backend
- REST API endpoints for programmatic access
