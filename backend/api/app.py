"""
FastAPI Web Application for Document Embedding Pipeline
Provides REST API for document upload, search, status, and deletion
"""
import os
import uuid
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.services.embedder import DocumentEmbedder
from backend.services.web_service import WebEmbeddingService

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Document Embedding Pipeline",
    description="Web interface for document embedding and semantic search",
    version="1.0.0"
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables (initialized on startup)
embedder: Optional[DocumentEmbedder] = None
service: Optional[WebEmbeddingService] = None
tasks_store: Dict[str, Dict] = {}
config: Dict = {}

# Constants
UPLOAD_DIR = Path("uploads")
MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
TASK_CLEANUP_HOURS = 1


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    global embedder, service, tasks_store, config

    # Create upload directory
    UPLOAD_DIR.mkdir(exist_ok=True)

    # Clean up old uploaded files (> 24 hours)
    cleanup_old_files()

    # Get LM Studio URL
    lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

    # Determine backend type - default to PostgreSQL
    backend_type = os.getenv("STORAGE_BACKEND", "postgresql")

    # Prepare backend kwargs (same pattern as CLI)
    backend_kwargs = {
        'backend_type': backend_type,
        # Supabase config
        'supabase_url': os.getenv("SUPABASE_URL"),
        'supabase_key': os.getenv("SUPABASE_KEY"),
        # PostgreSQL config
        'postgres_host': os.getenv("POSTGRES_HOST"),
        'postgres_port': int(os.getenv("POSTGRES_PORT", 5432)),
        'postgres_db': os.getenv("POSTGRES_DB"),
        'postgres_user': os.getenv("POSTGRES_USER"),
        'postgres_password': os.getenv("POSTGRES_PASSWORD"),
        'postgres_sslmode': os.getenv("POSTGRES_SSLMODE", "prefer"),
    }

    try:
        # Create embedder instance
        embedder = DocumentEmbedder(
            lm_studio_url=lm_studio_url,
            **backend_kwargs
        )

        # Create service instance
        service = WebEmbeddingService(embedder, tasks_store)

        # Store configuration for /api/config endpoint
        # Get actual backend type from embedder
        actual_backend = type(embedder.storage).__name__.replace('Backend', '').lower()

        config = {
            "lm_studio_url": lm_studio_url,
            "backend_type": actual_backend,
            "backend_type_config": backend_type,  # What was configured
            "chunk_size": int(os.getenv("CHUNK_SIZE", 1000)),
            "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", 200)),
            "chunking_strategy": os.getenv("CHUNKING_STRATEGY", "character"),
            "semantic_similarity_threshold": float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.75")),
            "table_name": os.getenv("TABLE_NAME", "documents"),
            "skip_if_exists": os.getenv("SKIP_IF_EXISTS", "true").lower() == "true",
            "available_backends": ["postgresql", "supabase"]
        }

        print(f"✓ Document Embedding Pipeline started successfully")
        print(f"  Backend: {config['backend_type']}")
        print(f"  LM Studio: {lm_studio_url}")
        print(f"  Chunking: {config['chunking_strategy']} (size: {config['chunk_size']})")

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease configure one of the following storage backends:")
        print("  - Supabase: SUPABASE_URL and SUPABASE_KEY")
        print("  - PostgreSQL: POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")
        raise


def cleanup_old_files():
    """Clean up uploaded files older than 24 hours"""
    if not UPLOAD_DIR.exists():
        return

    cutoff_time = datetime.now() - timedelta(hours=24)
    for file_path in UPLOAD_DIR.glob("*"):
        if file_path.is_file():
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff_time:
                try:
                    file_path.unlink()
                    print(f"Cleaned up old file: {file_path.name}")
                except Exception as e:
                    print(f"Failed to clean up {file_path.name}: {e}")


def cleanup_old_tasks():
    """Remove completed/failed tasks older than 1 hour"""
    cutoff_time = time.time() - (TASK_CLEANUP_HOURS * 3600)
    to_remove = []

    for task_id, task_data in tasks_store.items():
        if task_data.get("status") in ["completed", "failed"]:
            if task_data.get("created_at", 0) < cutoff_time:
                to_remove.append(task_id)

    for task_id in to_remove:
        del tasks_store[task_id]

    if to_remove:
        print(f"Cleaned up {len(to_remove)} old tasks")


@app.get("/")
async def read_root():
    """Serve frontend HTML"""
    return FileResponse("frontend/static/index.html")


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return config


@app.put("/api/config")
async def update_config(
    backend_type: str = Query(..., description="Backend type (postgresql or supabase)")
):
    """
    Update configuration (currently only backend_type is supported)

    This will reinitialize the embedder with the new backend
    """
    global embedder, service, config

    # Validate backend type
    if backend_type not in ["postgresql", "supabase"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid backend type. Must be 'postgresql' or 'supabase'"
        )

    try:
        # Get LM Studio URL
        lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

        # Prepare backend kwargs
        backend_kwargs = {
            'backend_type': backend_type,
            # Supabase config
            'supabase_url': os.getenv("SUPABASE_URL"),
            'supabase_key': os.getenv("SUPABASE_KEY"),
            # PostgreSQL config
            'postgres_host': os.getenv("POSTGRES_HOST"),
            'postgres_port': int(os.getenv("POSTGRES_PORT", 5432)),
            'postgres_db': os.getenv("POSTGRES_DB"),
            'postgres_user': os.getenv("POSTGRES_USER"),
            'postgres_password': os.getenv("POSTGRES_PASSWORD"),
            'postgres_sslmode': os.getenv("POSTGRES_SSLMODE", "prefer"),
        }

        # Create new embedder instance
        new_embedder = DocumentEmbedder(
            lm_studio_url=lm_studio_url,
            **backend_kwargs
        )

        # Update globals
        embedder = new_embedder
        service = WebEmbeddingService(embedder, tasks_store)

        # Get actual backend type from embedder
        actual_backend = type(embedder.storage).__name__.replace('Backend', '').lower()

        # Update config
        config["backend_type"] = actual_backend
        config["backend_type_config"] = backend_type

        print(f"✓ Backend switched to: {actual_backend}")

        return {
            "message": f"Backend successfully changed to {actual_backend}",
            "backend_type": actual_backend
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to initialize {backend_type} backend: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to change backend: {str(e)}"
        )


@app.post("/api/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and process a document

    Returns task_id for progress tracking
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file and check size
    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum: {MAX_FILE_SIZE_MB}MB"
        )

    # Save uploaded file with UUID prefix
    task_id = str(uuid.uuid4())
    upload_filename = f"{task_id}_{file.filename}"
    upload_path = UPLOAD_DIR / upload_filename

    with open(upload_path, "wb") as f:
        f.write(contents)

    # Initialize task in store
    tasks_store[task_id] = {
        "status": "processing",
        "created_at": time.time(),
        "filename": file.filename,
        "progress": {
            "stage": "queued",
            "message": "Queued for processing..."
        },
        "result": None,
        "error": None
    }

    # Get processing parameters from config
    table_name = config["table_name"]
    chunk_size = config["chunk_size"]
    overlap = config["chunk_overlap"]
    strategy = config["chunking_strategy"]
    similarity_threshold = config["semantic_similarity_threshold"]
    skip_if_exists = config["skip_if_exists"]

    # Start background processing
    background_tasks.add_task(
        service.process_document_with_progress,
        task_id=task_id,
        file_path=str(upload_path),
        table_name=table_name,
        chunk_size=chunk_size,
        overlap=overlap,
        strategy=strategy,
        similarity_threshold=similarity_threshold,
        skip_if_exists=skip_if_exists,
        document_name=file.filename  # Pass original filename for deduplication
    )

    # Clean up old tasks
    cleanup_old_tasks()

    return {
        "task_id": task_id,
        "filename": file.filename,
        "status": "processing"
    }


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status and progress"""
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="Task not found")

    return tasks_store[task_id]


@app.get("/api/documents")
async def get_documents():
    """List all processed documents"""
    try:
        table_name = config["table_name"]
        documents = embedder.storage.get_all_documents(table_name)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {str(e)}")


@app.delete("/api/documents/{document_name}")
async def delete_document(document_name: str):
    """Delete a document and all its chunks"""
    try:
        table_name = config["table_name"]

        # Check if document exists
        file_hash = embedder.storage.check_document_exists(document_name, table_name)
        if not file_hash:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete document chunks
        embedder.storage.delete_document_chunks(document_name, table_name)

        return {
            "message": "Document deleted successfully",
            "document_name": document_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@app.get("/api/search")
async def search_documents(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=50, description="Number of results to return")
):
    """
    Perform semantic search across all documents

    Returns similar chunks with relevance scores
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        table_name = config["table_name"]

        # Get embedding for query
        query_embedding = embedder.get_embedding(query)

        # Search similar chunks
        results = embedder.storage.search_similar_chunks(
            query_embedding=query_embedding,
            table_name=table_name,
            limit=limit
        )

        return results
    except Exception as e:
        # Check if it's an LM Studio connection error
        if "connection" in str(e).lower() or "refused" in str(e).lower():
            raise HTTPException(
                status_code=503,
                detail="Embedding server unavailable. Please ensure LM Studio is running."
            )
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# Mount static files (must be after route definitions)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEB_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
