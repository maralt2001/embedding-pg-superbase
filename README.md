# Document Embedding Pipeline

A comprehensive document embedding pipeline with CLI and web interface for processing, storing, and searching document embeddings using LM Studio.

## Project Structure

```
.
├── backend/                    # Backend services
│   ├── api/                   # FastAPI web application
│   │   └── app.py            # Main API endpoints
│   ├── services/              # Business logic
│   │   ├── embedder.py       # Document embedding service
│   │   └── web_service.py    # Web interface service layer
│   └── storage/               # Storage backends
│       └── backends.py        # Supabase & PostgreSQL implementations
│
├── frontend/                   # Frontend assets
│   └── static/                # HTML, CSS, JavaScript
│       ├── index.html        # Main web interface
│       ├── style.css         # Styling
│       └── app.js            # Frontend logic
│
├── scripts/                    # Utility scripts
│   ├── cli.py                # Command-line interface
│   └── main.py               # Legacy example script
│
├── uploads/                    # Temporary file uploads (gitignored)
├── run.py                      # Web server entry point
├── requirements.txt            # Python dependencies
├── .env                        # Configuration (not in git)
├── CLAUDE.md                   # Claude Code documentation
└── ROADMAP.md                  # Feature roadmap
```

## Quick Start

### 1. Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file with your configuration:

```bash
# Storage Backend (postgresql or supabase)
STORAGE_BACKEND=postgresql

# LM Studio
LM_STUDIO_URL=http://localhost:1234/v1

# PostgreSQL (if using postgresql backend)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=embeddings_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Supabase (if using supabase backend)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Processing settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
CHUNKING_STRATEGY=semantic
TABLE_NAME=documents
SKIP_IF_EXISTS=true
```

### 3. Run Web Interface

```bash
python run.py
```

Then open http://localhost:8000 in your browser.

### 4. Use CLI

```bash
# Embed documents
python scripts/cli.py embed document.pdf

# Search
python scripts/cli.py search "your query"

# Show status
python scripts/cli.py status

# Delete document
python scripts/cli.py delete document.pdf
```

## Features

- **Multiple Storage Backends**: PostgreSQL (default) or Supabase
- **Web Interface**: Modern UI with drag & drop upload, search, and management
- **Dynamic Backend Switching**: Change between PostgreSQL and Supabase without restart
- **CLI Interface**: Full command-line access to all features
- **Semantic Chunking**: 3 strategies (character, paragraph, semantic)
- **Incremental Updates**: Skip unchanged documents
- **Real-time Progress**: Visual feedback for document processing

## Documentation

See [CLAUDE.md](CLAUDE.md) for comprehensive documentation.

## Architecture

- **Backend**: FastAPI with async support, background task processing
- **Frontend**: Vanilla JavaScript (no build step required)
- **Storage**: Pluggable backends (PostgreSQL with pgvector, Supabase)
- **Embeddings**: LM Studio local embedding server

## Development

```bash
# Start web server with auto-reload
python run.py

# Or using uvicorn directly
uvicorn backend.api.app:app --reload

# Run CLI
python scripts/cli.py --help
```

## License

See project license file.
