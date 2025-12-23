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
│   ├── main.py               # Legacy example script
│   └── supabase_setup.sql    # Supabase database setup script
│
├── uploads/                    # Temporary file uploads (gitignored)
├── run.py                      # Web server entry point
├── requirements.txt            # Python dependencies
├── .env                        # Configuration (not in git)
├── .env.example                # Example configuration file
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

Create a `.env` file with your configuration (you can copy from `.env.example`):

```bash
# Environment (development or production)
ENVIRONMENT=development

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

# Web Server (optional overrides)
WEB_PORT=8000
# WEB_HOST=127.0.0.1  # Auto-configured based on ENVIRONMENT
# WEB_WORKERS=4       # Production only

# Processing settings
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
CHUNKING_STRATEGY=semantic
TABLE_NAME=documents
SKIP_IF_EXISTS=true
```

### 3. Run Web Interface

**Development mode** (localhost only, auto-reload):
```bash
python run.py
```

**Production mode** (network accessible, multi-worker):
```bash
ENVIRONMENT=production python run.py
```

Then open http://localhost:8000 in your browser (or http://your-server-ip:8000 in production).

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

## Docker Deployment

The application includes production-ready Docker support with multi-stage builds for optimal image size and security.

### Quick Start with Docker Compose (Recommended)

1. **Edit `docker-compose.yml`** with your configuration:
   ```yaml
   environment:
     - POSTGRES_HOST=your-postgres-host
     - POSTGRES_DB=embeddings_db
     - POSTGRES_PASSWORD=your-password
     - LM_STUDIO_URL=http://host.docker.internal:1234/v1
   ```

2. **Start the application**:
   ```bash
   docker-compose up -d
   ```

3. **Access the web interface**:
   ```
   http://localhost:8000
   ```

4. **View logs**:
   ```bash
   docker-compose logs -f
   ```

5. **Stop the application**:
   ```bash
   docker-compose down
   ```

### Manual Docker Build & Run

**Build the image**:
```bash
docker build -t embedding-pipeline:latest .
```

**Run with PostgreSQL**:
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

**Run with Supabase**:
```bash
docker run -d \
  -p 8000:8000 \
  -v ./uploads:/app/uploads \
  -e STORAGE_BACKEND=supabase \
  -e SUPABASE_URL=https://your-project.supabase.co \
  -e SUPABASE_KEY=your-key \
  -e LM_STUDIO_URL=http://host.docker.internal:1234/v1 \
  --name embedding-pipeline \
  embedding-pipeline:latest
```

### Docker Image Details

- **Base Image**: `python:3.11-slim-bookworm`
- **Image Size**: ~484MB (optimized multi-stage build)
- **Security**: Runs as non-root user (`appuser`)
- **Production Config**: 4 workers, runs on `0.0.0.0:8000`
- **Health Check**: Automatic health monitoring every 30s
- **Volumes**: `/app/uploads` for persistent file storage

### Configuration Notes

**LM Studio URL:**
- **Mac/Windows**: Use `http://host.docker.internal:1234/v1` (accesses host machine)
- **Linux**: Use `http://172.17.0.1:1234/v1` or your host IP

**Storage Options:**
- **Remote PostgreSQL**: Set `POSTGRES_HOST` to your database server
- **Supabase**: Set `STORAGE_BACKEND=supabase` with Supabase credentials
- **Local PostgreSQL**: Uncomment the postgres service in `docker-compose.yml`

### Common Docker Commands

```bash
# Check container status
docker ps
docker-compose ps

# View logs
docker logs embedding-pipeline
docker-compose logs -f embedding-pipeline

# Restart container
docker restart embedding-pipeline
docker-compose restart

# Stop and remove
docker rm -f embedding-pipeline
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Access container shell (for debugging)
docker exec -it embedding-pipeline /bin/bash
```

### Troubleshooting

**Can't connect to PostgreSQL:**
- Verify `POSTGRES_HOST` is accessible from the container
- Check firewall rules allow connection on port 5432
- Test: `docker-compose exec embedding-pipeline ping your-postgres-host`

**Can't connect to LM Studio:**
- Ensure LM Studio is running with API server enabled
- Use `host.docker.internal` (Mac/Windows) or `172.17.0.1` (Linux)
- Test: `docker-compose exec embedding-pipeline curl http://host.docker.internal:1234/v1/models`

**Permission errors:**
- The container runs as user `appuser` (UID 1000)
- Ensure the `uploads/` volume mount has proper permissions

## Features

- **Production Ready**: Environment-based configuration (development/production modes)
- **Docker Support**: Multi-stage builds, docker-compose, health checks
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
# Development mode (auto-reload enabled)
python run.py

# Production mode
ENVIRONMENT=production python run.py

# Or using uvicorn directly
uvicorn backend.api.app:app --reload  # Development
uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --workers 4  # Production

# Run CLI
python scripts/cli.py --help
```

**Environment Modes:**
- **Development**: `127.0.0.1:8000`, auto-reload, debug logging, 1 worker
- **Production**: `0.0.0.0:8000`, no reload, info logging, 4 workers

## License

See project license file.
