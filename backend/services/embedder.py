import os
import requests
from pathlib import Path
from typing import List, Dict, Optional
import fitz  # pymupdf
import docx
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.storage.backends import StorageBackend, create_storage_backend

class DocumentEmbedder:
    def __init__(self, lm_studio_url: str, storage_backend: StorageBackend = None,
                 embedding_model: str = None, **backend_kwargs):

        self.lm_studio_url = lm_studio_url

        # Get embedding model from parameter, env, or use default
        self.embedding_model = (
            embedding_model or
            os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
        )

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
            pdf_document = fitz.open(file_path)
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text.append(page.get_text())
            pdf_document.close()
            return '\n'.join(text)

        # Word documents
        elif file_path.suffix == '.docx':
            doc = docx.Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])

        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200,
                   strategy: str = "character", similarity_threshold: float = 0.75) -> List[str]:
        """
        Split text into chunks with specified strategy

        Args:
            text: The text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks (only for character strategy)
            strategy: Chunking strategy - "character", "paragraph", or "semantic"
            similarity_threshold: Similarity threshold for semantic chunking (0.0-1.0)

        Returns:
            List of text chunks (non-empty, stripped)
        """
        if strategy == "semantic":
            chunks = self._chunk_by_semantic(text, chunk_size, similarity_threshold)
        elif strategy == "paragraph":
            chunks = DocumentEmbedder._chunk_by_paragraph(text, chunk_size)
        else:
            # Character-based chunking (default)
            chunks = []
            start = 0

            while start < len(text):
                end = start + chunk_size
                chunk = text[start:end]
                chunks.append(chunk)
                start = end - overlap

        # Filter out empty chunks and strip whitespace
        original_count = len(chunks)
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

        if original_count > len(chunks):
            print(f"Warning: Removed {original_count - len(chunks)} empty chunk(s)")

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
    def _calculate_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Similarity score between -1 and 1 (higher = more similar)
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vectors must have same length: {len(vec1)} vs {len(vec2)}")

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(a * a for a in vec2) ** 0.5

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    def _split_into_sentences(text: str) -> List[str]:
        """
        Split text into sentences using regex pattern

        Handles:
        - Standard sentence endings (. ! ?)
        - Multiple punctuation (..., !!, etc.)
        - Common abbreviations (Dr., Mr., Ms., etc.)

        Args:
            text: Text to split

        Returns:
            List of sentences (stripped and non-empty)
        """
        import re

        # Replace common abbreviations to protect them
        protected_text = text
        abbreviations = [
            (r'\bDr\.', 'Dr<dot>'),
            (r'\bMr\.', 'Mr<dot>'),
            (r'\bMrs\.', 'Mrs<dot>'),
            (r'\bMs\.', 'Ms<dot>'),
            (r'\bProf\.', 'Prof<dot>'),
            (r'\betc\.', 'etc<dot>'),
            (r'\bi\.e\.', 'i<dot>e<dot>'),
            (r'\be\.g\.', 'e<dot>g<dot>'),
        ]

        for pattern, replacement in abbreviations:
            protected_text = re.sub(pattern, replacement, protected_text)

        # Split on sentence-ending punctuation followed by whitespace
        # Pattern: . ! ? followed by space and capital letter OR end of string
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$'
        sentences = re.split(sentence_pattern, protected_text)

        # Restore abbreviations and clean up
        result = []
        for sentence in sentences:
            # Restore protected dots
            restored = sentence.replace('<dot>', '.')
            cleaned = restored.strip()

            # Only include non-empty sentences
            if cleaned:
                result.append(cleaned)

        return result

    def _chunk_by_semantic(self, text: str, max_chunk_size: int = 1000,
                           similarity_threshold: float = 0.75) -> List[str]:
        """
        Split text into chunks based on semantic similarity

        Uses embedding similarity to group consecutive sentences that are
        semantically related, creating more coherent chunks.

        Args:
            text: Text to chunk
            max_chunk_size: Maximum size of each chunk in characters
            similarity_threshold: Minimum cosine similarity to merge sentences (0.0-1.0)

        Returns:
            List of semantically coherent text chunks
        """
        # Validate and clamp threshold
        if not 0.0 <= similarity_threshold <= 1.0:
            print(f"Warning: Similarity threshold {similarity_threshold} out of range, using 0.75")
            similarity_threshold = max(0.0, min(1.0, similarity_threshold))

        # Edge case: Very short text
        if len(text) < 100:
            return [text] if text.strip() else []

        # Step 1: Split into sentences
        sentences = self._split_into_sentences(text)

        if not sentences:
            return []

        if len(sentences) == 1:
            # Single sentence - split by size if needed
            if len(sentences[0]) <= max_chunk_size:
                return sentences
            else:
                # Fall back to character chunking for oversized single sentence
                print(f"Warning: Single sentence exceeds max_chunk_size, splitting by characters")
                chunks = []
                sentence = sentences[0]
                for i in range(0, len(sentence), max_chunk_size):
                    chunks.append(sentence[i:i+max_chunk_size])
                return chunks

        # Step 2: Generate embeddings for all sentences (BATCH MODE - much faster!)
        print(f"Generating embeddings for {len(sentences)} sentences using batch API...")

        try:
            # Use batch API - sends all sentences in one or more batches
            embeddings = self.get_embeddings_batch(sentences, batch_size=100)
            valid_sentences = sentences
            print(f"✓ Generated {len(embeddings)} embeddings in batch mode")

        except Exception as e:
            print(f"Warning: Batch embedding failed ({e}), falling back to individual requests...")

            # Fallback: Generate embeddings one by one
            embeddings = []
            valid_sentences = []

            for i, sentence in enumerate(sentences, 1):
                try:
                    if i % 50 == 0:  # Progress update every 50 sentences
                        print(f"  Progress: {i}/{len(sentences)} sentences")

                    embedding = self.get_embedding(sentence)
                    embeddings.append(embedding)
                    valid_sentences.append(sentence)
                except Exception as sentence_error:
                    print(f"Warning: Failed to get embedding for sentence {i}: {sentence_error}")
                    # Skip this sentence
                    continue

        if not valid_sentences:
            print("Error: No valid embeddings generated, falling back to character chunking")
            chunks = []
            for i in range(0, len(text), max_chunk_size):
                chunks.append(text[i:i+max_chunk_size])
            return chunks

        # Step 3: Group sentences by similarity
        chunks = []
        current_chunk = [valid_sentences[0]]
        current_size = len(valid_sentences[0])

        for i in range(1, len(valid_sentences)):
            sentence = valid_sentences[i]
            sentence_size = len(sentence)

            # Calculate similarity with previous sentence
            similarity = self._calculate_cosine_similarity(
                embeddings[i-1],
                embeddings[i]
            )

            # Decide: merge or start new chunk
            would_exceed = current_size + sentence_size + 1 > max_chunk_size  # +1 for space

            if similarity >= similarity_threshold and not would_exceed:
                # Merge into current chunk
                current_chunk.append(sentence)
                current_size += sentence_size + 1
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        print(f"Created {len(chunks)} semantic chunks (avg similarity threshold: {similarity_threshold})")
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
        """
        Get embedding vector for text using LM Studio

        Args:
            text: Text to embed (must be non-empty)

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If text is empty or only whitespace
            Exception: If API request fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        try:
            response = requests.post(
                f"{self.lm_studio_url}/embeddings",
                json={
                    "input": text,
                    "model": self.embedding_model
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            return data['data'][0]['embedding']
        except Exception as e:
            print(f"Error getting embedding: {e}")
            raise

    def _process_single_batch(self, batch: List[str], batch_index: int, total_batches: int) -> tuple[int, List[List[float]]]:
        """
        Process a single batch of texts (helper for parallel processing)

        Args:
            batch: List of texts to embed
            batch_index: Index of this batch (for ordering results)
            total_batches: Total number of batches (for progress reporting)

        Returns:
            Tuple of (batch_index, embeddings) to maintain order
        """
        try:
            response = requests.post(
                f"{self.lm_studio_url}/embeddings",
                json={
                    "input": batch,
                    "model": self.embedding_model
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()

            # Extract embeddings in order
            batch_embeddings = [item['embedding'] for item in data['data']]

            if total_batches > 1:
                print(f"  ✓ Batch {batch_index + 1}/{total_batches} completed ({len(batch)} texts)")

            return (batch_index, batch_embeddings)

        except Exception as e:
            print(f"  ✗ Error in batch {batch_index + 1}/{total_batches}: {e}")
            raise

    def get_embeddings_batch(self, texts: List[str], batch_size: int = 100,
                            max_workers: int = None) -> List[List[float]]:
        """
        Get embedding vectors for multiple texts using batch API with parallel processing

        Args:
            texts: List of texts to embed (must be non-empty)
            batch_size: Maximum texts per API request (default: 100)
            max_workers: Maximum parallel workers (default: from env or 4)

        Returns:
            List of embedding vectors (same order as input texts)

        Raises:
            ValueError: If any text is empty or only whitespace
            Exception: If API request fails
        """
        if not texts:
            return []

        # Validate all texts are non-empty
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Cannot generate embedding for empty text at index {i}")

        # Get max_workers from parameter, env, or default to 4
        if max_workers is None:
            max_workers = int(os.getenv("EMBEDDING_MAX_WORKERS", "4"))

        # Split into batches
        batches = []
        for i in range(0, len(texts), batch_size):
            batches.append(texts[i:i + batch_size])

        total_batches = len(batches)

        # If only one batch, no need for parallel processing
        if total_batches == 1:
            print(f"Processing single batch of {len(texts)} texts...")
            _, embeddings = self._process_single_batch(batches[0], 0, 1)
            return embeddings

        # Parallel processing for multiple batches
        print(f"Processing {total_batches} batches in parallel (max {max_workers} workers)...")

        # Store results with their original batch index
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batch processing tasks
            future_to_index = {
                executor.submit(self._process_single_batch, batch, i, total_batches): i
                for i, batch in enumerate(batches)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                batch_index, batch_embeddings = future.result()
                results[batch_index] = batch_embeddings

        # Reconstruct embeddings in original order
        all_embeddings = []
        for i in range(total_batches):
            all_embeddings.extend(results[i])

        print(f"✓ Completed all {total_batches} batches ({len(all_embeddings)} total embeddings)")
        return all_embeddings

    def process_document(self, file_path: str, table_name: str = "documents",
                         chunk_size: int = 1000, overlap: int = 200, strategy: str = "character",
                         similarity_threshold: float = 0.75, skip_if_exists: bool = True,
                         progress_callback=None, document_name: str = None):
        """
        Full pipeline: read document, chunk, embed, and upload

        Args:
            file_path: Path to the document
            table_name: Storage table name
            chunk_size: Size of text chunks
            overlap: Overlap between chunks (only used for character-based chunking)
            strategy: Chunking strategy - "character", "paragraph", or "semantic"
            similarity_threshold: Similarity threshold for semantic chunking (0.0-1.0)
            skip_if_exists: If True, skip processing if document hash hasn't changed
            progress_callback: Optional callback function(stage, message) for progress updates
            document_name: Optional document name to use instead of extracting from file_path
        """
        file_path_obj = Path(file_path)
        if document_name is None:
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
                    return {"skipped": True, "chunks_created": 0}
                else:
                    print(f"Document changed, updating: {document_name}")
                    self.storage.delete_document_chunks(document_name, table_name)
            else:
                print(f"New document, processing: {document_name}")

        if progress_callback:
            progress_callback("reading", "Reading document...")

        print(f"Reading document: {file_path}")
        text = self.read_document(file_path)

        if progress_callback:
            progress_callback("chunking", "Splitting document into chunks...")

        if strategy == "semantic":
            print(f"Chunking text by semantic similarity (threshold={similarity_threshold}, max_size={chunk_size})")
        elif strategy == "paragraph":
            print(f"Chunking text by paragraphs (max_chunk_size={chunk_size})")
        else:
            print(f"Chunking text by characters (chunk_size={chunk_size}, overlap={overlap})")

        chunks = self.chunk_text(text, chunk_size, overlap, strategy, similarity_threshold)
        print(f"Created {len(chunks)} chunks")

        print(f"Generating embeddings for {len(chunks)} chunks using batch API...")
        processed_at = datetime.utcnow().isoformat()

        if progress_callback:
            progress_callback("embedding", f"Generating embeddings for {len(chunks)} chunks...")

        # Generate all embeddings in batch mode (much faster!)
        try:
            embeddings = self.get_embeddings_batch(chunks, batch_size=100)
            print(f"✓ Generated {len(embeddings)} embeddings in batch mode")
        except Exception as e:
            print(f"Warning: Batch embedding failed ({e}), falling back to sequential processing...")
            embeddings = []
            for i, chunk in enumerate(chunks, 1):
                if progress_callback:
                    progress_callback("embedding", f"Generating embeddings... ({i}/{len(chunks)})")
                print(f"Processing chunk {i}/{len(chunks)}")
                embeddings.append(self.get_embedding(chunk))

        # Build chunks with embeddings
        chunks_with_embeddings = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings), 1):
            chunks_with_embeddings.append({
                "content": chunk,
                "embedding": embedding,
                "document_name": document_name,
                "chunk_index": i,
                "file_hash": current_hash,
                "processed_at": processed_at
            })

        if progress_callback:
            progress_callback("uploading", "Uploading chunks to database...")

        print("Uploading to storage...")
        self.storage.upload_chunks(chunks_with_embeddings, table_name)
        print("Done!")
        return {"skipped": False, "chunks_created": len(chunks)}