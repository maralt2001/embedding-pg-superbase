import requests
from pathlib import Path
from typing import List, Dict, Optional
import PyPDF2
import docx
import hashlib
from datetime import datetime
from storage_backends import StorageBackend, create_storage_backend

class DocumentEmbedder:
    def __init__(self, lm_studio_url: str, storage_backend: StorageBackend = None, **backend_kwargs):

        self.lm_studio_url = lm_studio_url

        # Use provided backend or create one from kwargs
        if storage_backend:
            self.storage = storage_backend
        else:
            self.storage = create_storage_backend(**backend_kwargs)

    @staticmethod
    def read_document(file_path: str) -> str:

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Text files
        if file_path.suffix == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

        # PDF files
        elif file_path.suffix == '.pdf':
            text = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)

        # Word documents
        elif file_path.suffix == '.docx':
            doc = docx.Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])

        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200, strategy: str = "character") -> List[str]:
        """
        Split text into chunks with overlap

        Args:
            text: The text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
            strategy: Chunking strategy - "character" or "paragraph"
        """
        if strategy == "paragraph":
            return DocumentEmbedder._chunk_by_paragraph(text, chunk_size)
        else:
            # Character-based chunking (default)
            chunks = []
            start = 0

            while start < len(text):
                end = start + chunk_size
                chunk = text[start:end]
                chunks.append(chunk)
                start = end - overlap

            return chunks

    @staticmethod
    def _chunk_by_paragraph(text: str, max_chunk_size: int = 1000) -> List[str]:
        """
        Split text into chunks based on paragraph boundaries

        Args:
            text: The text to chunk
            max_chunk_size: Maximum size of each chunk in characters

        Returns:
            List of text chunks respecting paragraph boundaries
        """
        # Split by double newlines (paragraph breaks) first, then single newlines
        paragraphs = text.split('\n\n')

        # Further split any remaining large paragraphs by single newlines
        refined_paragraphs = []
        for para in paragraphs:
            if para.strip():  # Skip empty paragraphs
                refined_paragraphs.append(para.strip())

        chunks = []
        current_chunk = []
        current_size = 0

        for para in refined_paragraphs:
            para_size = len(para)

            # If a single paragraph is larger than max_chunk_size, split it
            if para_size > max_chunk_size:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Split large paragraph by sentences or single newlines
                if '\n' in para:
                    sub_parts = para.split('\n')
                else:
                    # Split by periods if no newlines
                    sub_parts = [s.strip() + '.' for s in para.split('.') if s.strip()]

                temp_chunk = []
                temp_size = 0
                for part in sub_parts:
                    part_size = len(part)
                    if temp_size + part_size + 1 <= max_chunk_size:
                        temp_chunk.append(part)
                        temp_size += part_size + 1
                    else:
                        if temp_chunk:
                            chunks.append('\n'.join(temp_chunk) if '\n' in para else ' '.join(temp_chunk))
                        temp_chunk = [part]
                        temp_size = part_size

                if temp_chunk:
                    chunks.append('\n'.join(temp_chunk) if '\n' in para else ' '.join(temp_chunk))

            # If adding this paragraph would exceed max_chunk_size, start a new chunk
            elif current_size + para_size + 2 > max_chunk_size:  # +2 for '\n\n'
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for the '\n\n' separator

        # Add the last chunk if it has content
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Calculate SHA256 hash of a file

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash as hexadecimal string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_embedding(self, text: str) -> List[float]:

        try:
            response = requests.post(
                f"{self.lm_studio_url}/embeddings",
                json={
                    "input": text,
                    "model": "text-embedding-nomic-embed-text-v1.5"  # Adjust the model name as needed
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            return data['data'][0]['embedding']
        except Exception as e:
            print(f"Error getting embedding: {e}")
            raise

    def process_document(self, file_path: str, table_name: str = "documents",
                         chunk_size: int = 1000, overlap: int = 200, strategy: str = "character",
                         skip_if_exists: bool = True):
        """
        Full pipeline: read document, chunk, embed, and upload

        Args:
            file_path: Path to the document
            table_name: Storage table name
            chunk_size: Size of text chunks
            overlap: Overlap between chunks (only used for character-based chunking)
            strategy: Chunking strategy - "character" or "paragraph"
            skip_if_exists: If True, skip processing if document hash hasn't changed
        """
        file_path_obj = Path(file_path)
        document_name = file_path_obj.name

        # Calculate file hash
        print(f"Calculating file hash for: {document_name}")
        current_hash = self.calculate_file_hash(file_path)

        # Check if document already exists
        if skip_if_exists:
            existing_hash = self.storage.check_document_exists(document_name, table_name)

            if existing_hash:
                if existing_hash == current_hash:
                    print(f"✓ Document unchanged, skipping: {document_name}")
                    return "skipped"
                else:
                    print(f"Document changed, updating: {document_name}")
                    self.storage.delete_document_chunks(document_name, table_name)
            else:
                print(f"New document, processing: {document_name}")

        print(f"Reading document: {file_path}")
        text = self.read_document(file_path)

        if strategy == "paragraph":
            print(f"Chunking text by paragraphs (max_chunk_size={chunk_size})")
        else:
            print(f"Chunking text by characters (chunk_size={chunk_size}, overlap={overlap})")

        chunks = self.chunk_text(text, chunk_size, overlap, strategy)
        print(f"Created {len(chunks)} chunks")

        print("Generating embeddings...")
        chunks_with_embeddings = []
        processed_at = datetime.utcnow().isoformat()

        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}")
            embedding = self.get_embedding(chunk)
            chunks_with_embeddings.append({
                "content": chunk,
                "embedding": embedding,
                "document_name": document_name,
                "chunk_index": i,
                "file_hash": current_hash,
                "processed_at": processed_at
            })

        print("Uploading to storage...")
        self.storage.upload_chunks(chunks_with_embeddings, table_name)
        print("Done!")
        return "processed"