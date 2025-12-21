from abc import ABC, abstractmethod
from typing import List, Dict, Optional


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
    def search_similar_chunks(self, query_embedding: List[float], table_name: str, limit: int = 5) -> List[Dict]:
        """
        Search for similar chunks using cosine similarity

        Args:
            query_embedding: The embedding vector to search for
            table_name: Table name
            limit: Maximum number of results to return

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


class SupabaseBackend(StorageBackend):
    """Supabase storage backend implementation"""

    def __init__(self, supabase_url: str, supabase_key: str):
        from supabase import create_client, Client
        self.client: Client = create_client(supabase_url, supabase_key)

    def check_document_exists(self, document_name: str, table_name: str = "documents") -> Optional[str]:
        """Check if a document already exists in Supabase and return its hash"""
        try:
            response = self.client.table(table_name)\
                .select("file_hash")\
                .eq("document_name", document_name)\
                .limit(1)\
                .execute()

            if response.data and len(response.data) > 0:
                return response.data[0].get("file_hash")
            return None
        except Exception as e:
            print(f"Error checking document existence: {e}")
            return None

    def delete_document_chunks(self, document_name: str, table_name: str = "documents"):
        """Delete all chunks of a document from Supabase"""
        try:
            response = self.client.table(table_name)\
                .delete()\
                .eq("document_name", document_name)\
                .execute()
            print(f"Deleted existing chunks for: {document_name}")
            return response
        except Exception as e:
            print(f"Error deleting document chunks: {e}")
            raise

    def upload_chunks(self, chunks_with_embeddings: List[Dict], table_name: str = "documents"):
        """Upload chunks and embeddings to Supabase"""
        try:
            response = self.client.table(table_name).insert(chunks_with_embeddings).execute()
            print(f"Successfully uploaded {len(chunks_with_embeddings)} chunks to Supabase")
            return response
        except Exception as e:
            print(f"Error uploading to Supabase: {e}")
            raise

    def search_similar_chunks(self, query_embedding: List[float], table_name: str = "documents", limit: int = 5) -> List[Dict]:
        """Search for similar chunks using Supabase's vector similarity"""
        try:
            # Fetch all documents and calculate similarity in Python
            # This is less efficient but works without requiring SQL functions
            print("Fetching documents from Supabase...")

            response = self.client.table(table_name)\
                .select("id, content, document_name, chunk_index, embedding, file_hash, processed_at")\
                .execute()

            if not response.data:
                return []

            # Calculate cosine similarity for each document
            import math

            results = []
            for item in response.data:
                if 'embedding' not in item or not item['embedding']:
                    continue

                doc_embedding = item['embedding']

                # Convert embedding if it's a string (sometimes Supabase returns it as a string)
                if isinstance(doc_embedding, str):
                    import json
                    doc_embedding = json.loads(doc_embedding)

                # Ensure both embeddings are lists of floats
                doc_embedding = [float(x) for x in doc_embedding]
                query_emb = [float(x) for x in query_embedding]

                # Calculate cosine similarity
                dot_product = sum(a * b for a, b in zip(query_emb, doc_embedding))
                magnitude1 = math.sqrt(sum(a * a for a in query_emb))
                magnitude2 = math.sqrt(sum(a * a for a in doc_embedding))

                if magnitude1 == 0 or magnitude2 == 0:
                    similarity = 0.0
                else:
                    similarity = dot_product / (magnitude1 * magnitude2)

                item['similarity'] = similarity
                results.append(item)

            # Sort by similarity (highest first) and limit results
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:limit]

        except Exception as e:
            print(f"Error searching chunks: {e}")
            print("Note: This method fetches all chunks and calculates similarity in Python.")
            print("For better performance with large datasets, create the match_documents function.")
            print("See supabase_setup.sql for the SQL function definition")
            raise

    def get_all_documents(self, table_name: str = "documents") -> List[Dict]:
        """Get summary of all processed documents from Supabase"""
        try:
            # Group by document_name and get stats
            response = self.client.table(table_name)\
                .select("document_name, processed_at")\
                .execute()

            if not response.data:
                return []

            # Group documents manually since Supabase doesn't support GROUP BY in select
            docs_map = {}
            for row in response.data:
                doc_name = row['document_name']
                if doc_name not in docs_map:
                    docs_map[doc_name] = {
                        'document_name': doc_name,
                        'chunk_count': 0,
                        'processed_at': row['processed_at']
                    }
                docs_map[doc_name]['chunk_count'] += 1

            # Convert to list and sort by processed_at
            documents = list(docs_map.values())
            documents.sort(key=lambda x: x['processed_at'], reverse=True)

            return documents
        except Exception as e:
            print(f"Error fetching documents: {e}")
            raise


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
            print("PostgreSQL backend initialized with pgvector support")
        else:
            print("PostgreSQL backend initialized without pgvector (using REAL[] arrays)")

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
            print(f"Error checking pgvector extension: {e}")
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
        """Upload chunks and embeddings to PostgreSQL"""
        try:
            cursor = self.conn.cursor()

            # Prepare data for batch insert
            values = [
                (
                    chunk["content"],
                    chunk["embedding"],
                    chunk["document_name"],
                    chunk["chunk_index"],
                    chunk["file_hash"],
                    chunk["processed_at"]
                )
                for chunk in chunks_with_embeddings
            ]

            # Use executemany for efficient batch insert
            query = f"""
                INSERT INTO {table_name}
                (content, embedding, document_name, chunk_index, file_hash, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(query, values)
            self.conn.commit()
            cursor.close()

            print(f"Successfully uploaded {len(chunks_with_embeddings)} chunks to PostgreSQL")
        except Exception as e:
            self.conn.rollback()
            print(f"Error uploading to PostgreSQL: {e}")
            raise

    def search_similar_chunks(self, query_embedding: List[float], table_name: str = "documents", limit: int = 5) -> List[Dict]:
        """Search for similar chunks using cosine similarity"""
        try:
            cursor = self.conn.cursor()

            if self.has_pgvector:
                # Set ivfflat.probes to search more lists for better recall
                # This is especially important for small datasets or when using ivfflat indexes
                # Using 50 to ensure good recall even with small datasets
                cursor.execute("SET LOCAL ivfflat.probes = 50")

                # Use pgvector's cosine distance operator
                # Convert query_embedding to string representation for pgvector
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                query = f"""
                    SELECT
                        content,
                        document_name,
                        chunk_index,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM {table_name}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """
                cursor.execute(query, (embedding_str, embedding_str, limit))
            else:
                # Manual cosine similarity calculation for REAL[] arrays
                # Note: This is slower but works without pgvector
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
                    )
                    SELECT content, document_name, chunk_index, similarity
                    FROM similarities
                    ORDER BY similarity DESC
                    LIMIT %s
                """
                cursor.execute(query, (query_embedding, limit))

            rows = cursor.fetchall()
            cursor.close()

            # Convert to list of dicts
            results = []
            for row in rows:
                results.append({
                    'content': row[0],
                    'document_name': row[1],
                    'chunk_index': row[2],
                    'similarity': float(row[3])
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
    Factory function to create appropriate storage backend

    Args:
        backend_type: "supabase" or "postgresql" (optional, auto-detected if not provided)
        supabase_url: Supabase URL (for Supabase backend)
        supabase_key: Supabase API key (for Supabase backend)
        postgres_host: PostgreSQL host (for PostgreSQL backend)
        postgres_port: PostgreSQL port (for PostgreSQL backend)
        postgres_db: PostgreSQL database name (for PostgreSQL backend)
        postgres_user: PostgreSQL username (for PostgreSQL backend)
        postgres_password: PostgreSQL password (for PostgreSQL backend)
        postgres_sslmode: PostgreSQL SSL mode (for PostgreSQL backend, optional)

    Returns:
        StorageBackend instance (either SupabaseBackend or PostgreSQLBackend)

    Raises:
        ValueError: If backend type cannot be determined or required credentials are missing
    """
    backend_type = kwargs.get('backend_type')

    # Auto-detect backend type if not specified
    if not backend_type:
        if kwargs.get('supabase_url') and kwargs.get('supabase_key'):
            backend_type = 'supabase'
        elif kwargs.get('postgres_host'):
            backend_type = 'postgresql'
        else:
            raise ValueError(
                "Could not determine storage backend. Please set STORAGE_BACKEND environment variable "
                "or provide either (SUPABASE_URL and SUPABASE_KEY) or POSTGRES_HOST."
            )

    # Create appropriate backend
    if backend_type == 'supabase':
        supabase_url = kwargs.get('supabase_url')
        supabase_key = kwargs.get('supabase_key')

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase backend requires SUPABASE_URL and SUPABASE_KEY")

        print(f"Using Supabase storage backend")
        return SupabaseBackend(
            supabase_url=supabase_url,
            supabase_key=supabase_key
        )

    elif backend_type == 'postgresql':
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

        print(f"Using PostgreSQL storage backend (host={postgres_host}, db={postgres_db})")
        return PostgreSQLBackend(
            host=postgres_host,
            port=postgres_port,
            database=postgres_db,
            user=postgres_user,
            password=postgres_password,
            sslmode=postgres_sslmode
        )

    else:
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Supported backends: 'supabase', 'postgresql'"
        )
