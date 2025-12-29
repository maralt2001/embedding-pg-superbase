"""
FastAPI Web Application for Document Embedding Pipeline
Provides REST API for document upload, search, status, and deletion
"""
import os
import uuid
import time
import logging
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

    # Prepare backend kwargs (PostgreSQL only)
    backend_kwargs = {
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
        config = {
            "lm_studio_url": lm_studio_url,
            "embedding_model": embedder.embedding_model,
            "backend_type": "postgresql",
            "chunk_size": int(os.getenv("CHUNK_SIZE", 1000)),
            "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", 200)),
            "chunking_strategy": os.getenv("CHUNKING_STRATEGY", "character"),
            "semantic_similarity_threshold": float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.75")),
            "table_name": os.getenv("TABLE_NAME", "documents"),
            "skip_if_exists": os.getenv("SKIP_IF_EXISTS", "true").lower() == "true"
        }

        # Log startup info (once per worker)
        worker_id = os.getpid()
        logger = logging.getLogger("uvicorn.error")
        logger.info(f"Worker {worker_id}: Initialized PostgreSQL backend with {config['chunking_strategy']} chunking")

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease configure PostgreSQL backend:")
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
    limit: int = Query(5, ge=1, le=50, description="Number of results to return"),
    document: Optional[str] = Query(None, description="Filter results to specific document"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum similarity score (0.0-1.0)")
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

        # Search similar chunks with filters
        results = embedder.storage.search_similar_chunks(
            query_embedding=query_embedding,
            table_name=table_name,
            limit=limit,
            document_name=document,
            min_score=min_score
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


@app.post("/api/chat")
async def chat_with_documents(
    query: str = Query(..., description="User question"),
    limit: int = Query(5, ge=1, le=20, description="Number of context chunks to retrieve"),
    document: Optional[str] = Query(None, description="Filter context to specific document"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum similarity score for context (0.0-1.0)")
):
    """
    Chat with documents using RAG (Retrieval Augmented Generation) with streaming

    Retrieves relevant chunks and uses LLM to answer based on context
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        import requests
        import json
        from fastapi.responses import StreamingResponse

        table_name = config["table_name"]

        # Get embedding for query
        query_embedding = embedder.get_embedding(query)

        # Search similar chunks with filters
        results = embedder.storage.search_similar_chunks(
            query_embedding=query_embedding,
            table_name=table_name,
            limit=limit,
            document_name=document,
            min_score=min_score
        )

        # Build context from results
        documents_found = bool(results)

        if not results:
            context = "No relevant documents found."
            sources = []
        else:
            context_parts = []
            sources = []
            for i, result in enumerate(results, 1):
                context_parts.append(f"[Document {i}: {result['document_name']}]\n{result['content']}")
                sources.append({
                    "document_name": result["document_name"],
                    "chunk_index": result.get("chunk_index", 0),
                    "similarity_score": result.get("similarity_score", 0)
                })
            context = "\n\n".join(context_parts)

        # Construct prompt based on whether documents were found
        if documents_found:
            system_prompt = """You are a helpful assistant that answers questions based on the provided document context.
Always base your answers primarily on the provided documents. If additional context would be helpful, you may supplement with general knowledge, but make it clear what comes from the documents versus general knowledge."""

            user_prompt = f"""Context from documents:
{context}

Question: {query}

Please provide a detailed answer based on the context above."""
        else:
            system_prompt = """You are a helpful assistant. Answer questions using your general knowledge.
IMPORTANT: You must start your response by informing the user that no relevant information was found in the uploaded documents, and that you are answering based on general knowledge instead."""

            user_prompt = f"""Question: {query}

Note: No relevant documents were found in the database for this question. Please answer using your general knowledge, but inform the user about this."""

        # Stream generator function
        def generate_stream():
            try:
                # First send sources as metadata
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

                # Call LM Studio chat completion with streaming
                lm_studio_url = config["lm_studio_url"]
                chat_url = lm_studio_url.replace("/v1", "") + "/v1/chat/completions"

                response = requests.post(
                    chat_url,
                    json={
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1000,
                        "stream": True
                    },
                    stream=True,
                    timeout=60
                )

                if response.status_code != 200:
                    yield f"data: {json.dumps({'type': 'error', 'error': f'LM Studio returned status {response.status_code}'})}\n\n"
                    return

                # Stream the response
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            data_str = line_text[6:]  # Remove 'data: ' prefix
                            if data_str.strip() == '[DONE]':
                                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                                break
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                            except json.JSONDecodeError:
                                continue

            except requests.exceptions.ConnectionError:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Chat server unavailable. Please ensure LM Studio is running with a chat model loaded.'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# Mount static files (must be after route definitions)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEB_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
