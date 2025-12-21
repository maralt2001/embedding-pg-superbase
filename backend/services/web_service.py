"""
Web Embedding Service
Provides progress tracking wrapper around DocumentEmbedder for web interface
"""
import os
import time
from pathlib import Path
from typing import Dict, Optional, Callable
from backend.services.embedder import DocumentEmbedder


class WebEmbeddingService:
    """
    Service layer for web interface providing progress tracking
    and task management for document processing
    """

    def __init__(self, embedder: DocumentEmbedder, tasks_store: Dict):
        """
        Initialize web embedding service

        Args:
            embedder: DocumentEmbedder instance
            tasks_store: Shared dict for task status tracking
        """
        self.embedder = embedder
        self.tasks_store = tasks_store

    def process_document_with_progress(
        self,
        task_id: str,
        file_path: str,
        table_name: str,
        chunk_size: int,
        overlap: int,
        strategy: str,
        similarity_threshold: float,
        skip_if_exists: bool,
        document_name: str = None
    ):
        """
        Process document with progress tracking

        Updates tasks_store at each stage of processing

        Args:
            task_id: Unique task identifier
            file_path: Path to document file
            table_name: Storage table name
            chunk_size: Chunk size in characters
            overlap: Chunk overlap (for character strategy)
            strategy: Chunking strategy (character/paragraph/semantic)
            similarity_threshold: Threshold for semantic chunking
            skip_if_exists: Whether to skip unchanged documents
            document_name: Optional document name (defaults to filename from path)
        """
        start_time = time.time()

        try:
            # Update: Reading
            self._update_progress(task_id, "reading", "Reading document...")

            # Call DocumentEmbedder with progress callback
            def progress_callback(stage: str, message: str):
                self._update_progress(task_id, stage, message)

            result = self.embedder.process_document(
                file_path=file_path,
                table_name=table_name,
                chunk_size=chunk_size,
                overlap=overlap,
                strategy=strategy,
                similarity_threshold=similarity_threshold,
                skip_if_exists=skip_if_exists,
                progress_callback=progress_callback,
                document_name=document_name
            )

            # Calculate processing time
            processing_time = time.time() - start_time

            # Update: Completed
            # Use provided document_name or extract from path
            result_doc_name = document_name if document_name else Path(file_path).name
            self._update_completed(
                task_id,
                {
                    "document_name": result_doc_name,
                    "chunks_created": result.get("chunks_created", 0) if result else 0,
                    "processing_time": round(processing_time, 2),
                    "skipped": result.get("skipped", False) if result else False
                }
            )

        except Exception as e:
            # Update: Failed
            self._update_failed(task_id, str(e))
            raise

        finally:
            # Clean up uploaded file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Failed to clean up file {file_path}: {e}")

    def _update_progress(self, task_id: str, stage: str, message: str):
        """
        Update task progress in store

        Args:
            task_id: Task identifier
            stage: Current processing stage
            message: Progress message
        """
        if task_id in self.tasks_store:
            self.tasks_store[task_id]["status"] = "processing"
            self.tasks_store[task_id]["progress"] = {
                "stage": stage,
                "message": message
            }

    def _update_completed(self, task_id: str, result: Dict):
        """
        Update task as completed

        Args:
            task_id: Task identifier
            result: Processing result data
        """
        if task_id in self.tasks_store:
            self.tasks_store[task_id]["status"] = "completed"
            self.tasks_store[task_id]["result"] = result
            self.tasks_store[task_id]["progress"] = {
                "stage": "completed",
                "message": "Processing completed successfully"
            }

    def _update_failed(self, task_id: str, error: str):
        """
        Update task as failed

        Args:
            task_id: Task identifier
            error: Error message
        """
        if task_id in self.tasks_store:
            self.tasks_store[task_id]["status"] = "failed"
            self.tasks_store[task_id]["error"] = error
            self.tasks_store[task_id]["progress"] = {
                "stage": "failed",
                "message": f"Processing failed: {error}"
            }
