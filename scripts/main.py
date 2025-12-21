"""
Example-Script using the Document Embedder with environment variables
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from backend.services.embedder import DocumentEmbedder

load_dotenv()


def main():
    # configuration from environment variables
    lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
    backend_type = os.getenv("STORAGE_BACKEND")

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

    # initialize the embedder
    try:
        embedder = DocumentEmbedder(
            lm_studio_url=lm_studio_url,
            **backend_kwargs
        )
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease configure one of the following storage backends in your .env file:")
        print("  - Supabase: Set SUPABASE_URL and SUPABASE_KEY")
        print("  - PostgreSQL: Set POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD")
        return

    # Optional parameters from environment variables
    chunk_size = int(os.getenv("CHUNK_SIZE"))
    overlap = int(os.getenv("CHUNK_OVERLAP"))
    table_name = os.getenv("TABLE_NAME")
    chunking_strategy = os.getenv("CHUNKING_STRATEGY", "character")  # Default to "character"
    similarity_threshold = float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.75"))  # Default to 0.75
    skip_if_exists = os.getenv("SKIP_IF_EXISTS", "true").lower() == "true"  # Default to True

    # Example working with a local file
    document_path = "content/created/ansible_info.pdf"  # point to your local file here

    print(f"Start processing: {document_path}")
    print(f"Chunk size: {chunk_size}, Overlap: {overlap}")
    print(f"Chunking strategy: {chunking_strategy}")
    if chunking_strategy == "semantic":
        print(f"Similarity threshold: {similarity_threshold}")
    print(f"Skip if unchanged: {skip_if_exists}")
    print(f"Target table: {table_name}\n")

    try:
        result = embedder.process_document(
            file_path=document_path,
            table_name=table_name,
            chunk_size=chunk_size,
            overlap=overlap,
            strategy=chunking_strategy,
            similarity_threshold=similarity_threshold,
            skip_if_exists=skip_if_exists
        )

        if result == "skipped":
            print("\n⊘ Skipped (no changes)")
        else:
            print("\n✓ Success!")

    except FileNotFoundError:
        print(f"\n✗ Error: File '{document_path}' not found")
        print("Tip: Adjust the 'document_path' in this script")

    except Exception as e:
        print(f"\n✗ Error during processing: {e}")


if __name__ == "__main__":
    main()