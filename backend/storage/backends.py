from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging
from io import StringIO
import json

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    def check_document_exists(self, document_name: str, table_name: str) -> Optional[str]:
        """
        Check if a document already exists and return its hash

        Args:
            document_name: Name of the document
            table_name: Table name

        Returns:
            File hash if document exists, None otherwise
        """
        pass

    @abstractmethod
    def delete_document_chunks(self, document_name: str, table_name: str):
        """
        Delete all chunks of a document

        Args:
            document_name: Name of the document to delete
            table_name: Table name
        """
        pass

    @abstractmethod
    def upload_chunks(self, chunks_with_embeddings: List[Dict], table_name: str):
        """
        Upload chunks with embeddings

        Args:
            chunks_with_embeddings: List of dicts with 'content', 'embedding', etc.
            table_name: Table name
        """
        pass

    @abstractmethod
    def search_similar_chunks(self, query_embedding: List[float], table_name: str, limit: int = 5,
                            document_name: Optional[str] = None, min_score: Optional[float] = None) -> List[Dict]:
        """
        Search for similar chunks using cosine similarity

        Args:
            query_embedding: The embedding vector to search for
            table_name: Table name
            limit: Maximum number of results to return
            document_name: Optional filter to search only in specific document
            min_score: Optional minimum similarity score (0.0-1.0)

        Returns:
            List of dicts with 'content', 'document_name', 'chunk_index', 'similarity'
        """
        pass

    @abstractmethod
    def get_all_documents(self, table_name: str) -> List[Dict]:
        """
        Get summary of all processed documents

        Args:
            table_name: Table name

        Returns:
            List of dicts with 'document_name', 'chunk_count', 'processed_at'
        """
        pass


class PostgreSQLBackend(StorageBackend):
    """PostgreSQL storage backend implementation"""

    def __init__(self, host: str, port: int, database: str, user: str, password: str, sslmode: str = "prefer"):
        import psycopg2

        self.conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=database,
            user=user,
            password=password,
            sslmode=sslmode
        )
        self.has_pgvector = self._check_pgvector_extension()

        if self.has_pgvector:
            logger.debug("PostgreSQL backend initialized with pgvector support")
        else:
            logger.debug("PostgreSQL backend initialized without pgvector (using REAL[] arrays)")

    def _check_pgvector_extension(self) -> bool:
        """Check if pgvector extension is available"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                );
            """)
            result = cursor.fetchone()[0]
            cursor.close()
            return result
        except Exception as e:
            logger.warning(f"Error checking pgvector extension: {e}")
            return False

    def check_document_exists(self, document_name: str, table_name: str = "documents") -> Optional[str]:
        """Check if a document already exists in PostgreSQL and return its hash"""
        try:
            cursor = self.conn.cursor()
            query = f"SELECT file_hash FROM {table_name} WHERE document_name = %s LIMIT 1"
            cursor.execute(query, (document_name,))
            row = cursor.fetchone()
            cursor.close()

            if row:
                return row[0]
            return None
        except Exception as e:
            print(f"Error checking document existence: {e}")
            return None

    def delete_document_chunks(self, document_name: str, table_name: str = "documents"):
        """Delete all chunks of a document from PostgreSQL"""
        try:
            cursor = self.conn.cursor()
            query = f"DELETE FROM {table_name} WHERE document_name = %s"
            cursor.execute(query, (document_name,))
            self.conn.commit()
            cursor.close()
            print(f"Deleted existing chunks for: {document_name}")
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting document chunks: {e}")
            raise

    def upload_chunks(self, chunks_with_embeddings: List[Dict], table_name: str = "documents"):
        """Upload chunks and embeddings to PostgreSQL using optimized COPY"""
        if not chunks_with_embeddings:
            return

        num_chunks = len(chunks_with_embeddings)

        try:
            # Try PostgreSQL COPY first (fastest - 10-50x faster than INSERT)
            self._upload_with_copy(chunks_with_embeddings, table_name)
            print(f"✓ Successfully uploaded {num_chunks} chunks using COPY (optimized)")

        except Exception as copy_error:
            logger.warning(f"COPY failed ({copy_error}), falling back to execute_values...")

            try:
                # Fallback to execute_values (2-5x faster than executemany)
                self._upload_with_execute_values(chunks_with_embeddings, table_name)
                print(f"✓ Successfully uploaded {num_chunks} chunks using execute_values")

            except Exception as values_error:
                logger.warning(f"execute_values failed ({values_error}), falling back to executemany...")

                # Final fallback to executemany (slowest but most compatible)
                self._upload_with_executemany(chunks_with_embeddings, table_name)
                print(f"✓ Successfully uploaded {num_chunks} chunks using executemany")

    def _upload_with_copy(self, chunks_with_embeddings: List[Dict], table_name: str):
        """Upload using PostgreSQL COPY FROM STDIN (fastest method)"""
        cursor = self.conn.cursor()

        try:
            # Create CSV-like data stream
            buffer = StringIO()

            for chunk in chunks_with_embeddings:
                # Convert embedding array to pgvector format: [1,2,3]
                # Note: Use [...] for vector type, {...} for array type
                embedding_str = '[' + ','.join(map(str, chunk['embedding'])) + ']'

                # For COPY TEXT format, escape backslash, newline, carriage return, and tab
                # Also remove null bytes that PostgreSQL can't handle
                content = chunk['content'].replace('\x00', '').replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                document_name = chunk['document_name'].replace('\\', '\\\\').replace('\t', '\\t')
                file_hash = chunk['file_hash'].replace('\\', '\\\\').replace('\t', '\\t')
                processed_at = chunk['processed_at'].replace('\\', '\\\\').replace('\t', '\\t')

                # Write tab-separated values
                buffer.write(f"{content}\t{embedding_str}\t{document_name}\t{chunk['chunk_index']}\t{file_hash}\t{processed_at}\n")

            # Reset buffer position
            buffer.seek(0)

            # Use COPY FROM STDIN
            cursor.copy_from(
                buffer,
                table_name,
                columns=('content', 'embedding', 'document_name', 'chunk_index', 'file_hash', 'processed_at'),
                sep='\t'
            )

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def _upload_with_execute_values(self, chunks_with_embeddings: List[Dict], table_name: str):
        """Upload using psycopg2.extras.execute_values (medium speed)"""
        from psycopg2.extras import execute_values

        cursor = self.conn.cursor()

        try:
            # Prepare data tuples
            # Sanitize content to remove null bytes that PostgreSQL can't handle
            values = [
                (
                    chunk["content"].replace('\x00', ''),  # Remove null bytes as backup
                    chunk["embedding"],
                    chunk["document_name"],
                    chunk["chunk_index"],
                    chunk["file_hash"],
                    chunk["processed_at"]
                )
                for chunk in chunks_with_embeddings
            ]

            # Use execute_values for batch insert
            query = f"""
                INSERT INTO {table_name}
                (content, embedding, document_name, chunk_index, file_hash, processed_at)
                VALUES %s
            """
            execute_values(cursor, query, values)

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def _upload_with_executemany(self, chunks_with_embeddings: List[Dict], table_name: str):
        """Upload using executemany (slowest but most compatible)"""
        cursor = self.conn.cursor()

        try:
            # Prepare data tuples
            # Sanitize content to remove null bytes that PostgreSQL can't handle
            values = [
                (
                    chunk["content"].replace('\x00', ''),  # Remove null bytes as backup
                    chunk["embedding"],
                    chunk["document_name"],
                    chunk["chunk_index"],
                    chunk["file_hash"],
                    chunk["processed_at"]
                )
                for chunk in chunks_with_embeddings
            ]

            # Use executemany for batch insert
            query = f"""
                INSERT INTO {table_name}
                (content, embedding, document_name, chunk_index, file_hash, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(query, values)

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()

    def search_similar_chunks(self, query_embedding: List[float], table_name: str = "documents", limit: int = 5,
                            document_name: Optional[str] = None, min_score: Optional[float] = None) -> List[Dict]:
        """Search for similar chunks using cosine similarity with optional filters"""
        try:
            cursor = self.conn.cursor()

            if self.has_pgvector:
                # Set ivfflat.probes to search more lists for better recall
                cursor.execute("SET LOCAL ivfflat.probes = 50")

                # Use pgvector's cosine distance operator
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

                # Build WHERE clause and parameters in correct order
                where_clauses = []
                where_params = []

                if document_name:
                    where_clauses.append("document_name = %s")
                    where_params.append(document_name)

                if min_score is not None:
                    # Convert min_score to max distance (1 - similarity = distance)
                    max_distance = 1.0 - min_score
                    where_clauses.append("(embedding <=> %s::vector) <= %s")
                    where_params.extend([embedding_str, max_distance])

                where_clause = " AND ".join(where_clauses) if where_clauses else ""
                where_sql = f"WHERE {where_clause}" if where_clause else ""

                # Build parameter list in correct order for query placeholders
                params = [embedding_str] + where_params + [embedding_str, limit]

                query = f"""
                    SELECT
                        content,
                        document_name,
                        chunk_index,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM {table_name}
                    {where_sql}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                cursor.execute(query, params)
            else:
                # Manual cosine similarity calculation for REAL[] arrays
                where_clauses = []

                if document_name:
                    where_clauses.append("document_name = %s")

                where_clause = " AND ".join(where_clauses) if where_clauses else ""
                where_sql = f"WHERE {where_clause}" if where_clause else ""

                query = f"""
                    WITH query_vec AS (
                        SELECT %s::real[] as vec
                    ),
                    similarities AS (
                        SELECT
                            content,
                            document_name,
                            chunk_index,
                            embedding,
                            (
                                -- Dot product
                                (SELECT SUM(a * b)
                                 FROM unnest(embedding) WITH ORDINALITY AS t1(a, i)
                                 JOIN unnest((SELECT vec FROM query_vec)) WITH ORDINALITY AS t2(b, j)
                                 ON t1.i = t2.j)
                                /
                                -- Magnitude product
                                (
                                    SQRT((SELECT SUM(a * a) FROM unnest(embedding) AS a)) *
                                    SQRT((SELECT SUM(b * b) FROM unnest((SELECT vec FROM query_vec)) AS b))
                                )
                            ) as similarity
                        FROM {table_name}
                        {where_sql}
                    )
                    SELECT content, document_name, chunk_index, similarity
                    FROM similarities
                """

                params = [query_embedding]

                if document_name:
                    params.append(document_name)

                if min_score is not None:
                    query += " WHERE similarity >= %s"
                    params.append(min_score)

                query += """
                    ORDER BY similarity DESC
                    LIMIT %s
                """
                params.append(limit)

                cursor.execute(query, params)

            rows = cursor.fetchall()
            cursor.close()

            # Convert to list of dicts
            results = []
            for row in rows:
                results.append({
                    'content': row[0],
                    'document_name': row[1],
                    'chunk_index': row[2],
                    'similarity_score': float(row[3])  # Renamed from 'similarity' for clarity
                })

            return results
        except Exception as e:
            print(f"Error searching chunks: {e}")
            raise

    def get_all_documents(self, table_name: str = "documents") -> List[Dict]:
        """Get summary of all processed documents from PostgreSQL"""
        try:
            cursor = self.conn.cursor()
            query = f"""
                SELECT
                    document_name,
                    COUNT(*) as chunk_count,
                    MAX(processed_at) as processed_at
                FROM {table_name}
                GROUP BY document_name
                ORDER BY processed_at DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()

            # Convert to list of dicts
            documents = []
            for row in rows:
                documents.append({
                    'document_name': row[0],
                    'chunk_count': row[1],
                    'processed_at': row[2]
                })

            return documents
        except Exception as e:
            print(f"Error fetching documents: {e}")
            raise

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()


def create_storage_backend(**kwargs) -> StorageBackend:
    """
    Factory function to create PostgreSQL storage backend

    Args:
        postgres_host: PostgreSQL host
        postgres_port: PostgreSQL port (default: 5432)
        postgres_db: PostgreSQL database name
        postgres_user: PostgreSQL username
        postgres_password: PostgreSQL password
        postgres_sslmode: PostgreSQL SSL mode (optional, default: "prefer")

    Returns:
        PostgreSQLBackend instance

    Raises:
        ValueError: If required credentials are missing
    """
    postgres_host = kwargs.get('postgres_host')
    postgres_port = kwargs.get('postgres_port', 5432)
    postgres_db = kwargs.get('postgres_db')
    postgres_user = kwargs.get('postgres_user')
    postgres_password = kwargs.get('postgres_password')
    postgres_sslmode = kwargs.get('postgres_sslmode', 'prefer')

    if not all([postgres_host, postgres_db, postgres_user, postgres_password]):
        raise ValueError(
            "PostgreSQL backend requires POSTGRES_HOST, POSTGRES_DB, "
            "POSTGRES_USER, and POSTGRES_PASSWORD"
        )

    logger.debug(f"Initializing PostgreSQL backend (host={postgres_host}, db={postgres_db})")
    return PostgreSQLBackend(
        host=postgres_host,
        port=postgres_port,
        database=postgres_db,
        user=postgres_user,
        password=postgres_password,
        sslmode=postgres_sslmode
    )
