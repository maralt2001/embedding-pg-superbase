#!/usr/bin/env python3
"""
CLI for Document Embedding Pipeline
Supports: embed, search, and status commands
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
from dotenv import load_dotenv
from backend.services.embedder import DocumentEmbedder
from backend.storage.backends import create_storage_backend

load_dotenv()


def create_embedder_from_args(args):
    """Create DocumentEmbedder from command-line arguments and environment"""
    # Get LM Studio URL from args or environment
    lm_studio_url = args.lm_studio_url or os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

    # Prepare backend kwargs (PostgreSQL only)
    backend_kwargs = {
        'postgres_host': args.postgres_host or os.getenv("POSTGRES_HOST"),
        'postgres_port': args.postgres_port or int(os.getenv("POSTGRES_PORT", 5432)),
        'postgres_db': args.postgres_db or os.getenv("POSTGRES_DB"),
        'postgres_user': args.postgres_user or os.getenv("POSTGRES_USER"),
        'postgres_password': args.postgres_password or os.getenv("POSTGRES_PASSWORD"),
        'postgres_sslmode': args.postgres_sslmode or os.getenv("POSTGRES_SSLMODE", "prefer"),
    }

    try:
        embedder = DocumentEmbedder(
            lm_studio_url=lm_studio_url,
            **backend_kwargs
        )
        return embedder
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease configure PostgreSQL backend:")
        print("  - Via .env file (recommended)")
        print("  - Via command-line arguments (--postgres-host, --postgres-db, etc.)")
        print("\nRun with --help for more information")
        sys.exit(1)


def cmd_embed(args):
    """Handle 'embed' command - process documents and generate embeddings"""
    embedder = create_embedder_from_args(args)

    # Get parameters from args or environment
    chunk_size = args.chunk_size or int(os.getenv("CHUNK_SIZE", 1000))
    overlap = args.overlap or int(os.getenv("CHUNK_OVERLAP", 200))
    table_name = args.table or os.getenv("TABLE_NAME", "documents")
    chunking_strategy = args.strategy or os.getenv("CHUNKING_STRATEGY", "character")
    similarity_threshold = args.similarity_threshold or float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.75"))
    skip_if_exists = not args.force  # Force flag overrides skip behavior

    # Handle multiple documents or directory
    file_paths = []

    if args.directory:
        # Process all supported files in directory
        directory = Path(args.directory)
        if not directory.is_dir():
            print(f"Error: '{args.directory}' is not a directory")
            sys.exit(1)

        supported_extensions = ['.pdf', '.docx', '.txt']
        for ext in supported_extensions:
            file_paths.extend(directory.glob(f'*{ext}'))

        if not file_paths:
            print(f"No supported documents found in '{args.directory}'")
            print(f"Supported formats: {', '.join(supported_extensions)}")
            sys.exit(1)
    else:
        # Process individual file(s)
        file_paths = [Path(f) for f in args.files]

    # Print configuration
    print(f"Configuration:")
    print(f"  LM Studio URL: {embedder.lm_studio_url}")
    print(f"  Table: {table_name}")
    print(f"  Chunk size: {chunk_size}")
    print(f"  Overlap: {overlap}")
    print(f"  Chunking strategy: {chunking_strategy}")
    if chunking_strategy == "semantic":
        print(f"  Similarity threshold: {similarity_threshold}")
    print(f"  Skip unchanged: {skip_if_exists}")
    print(f"  Files to process: {len(file_paths)}\n")

    # Process each document
    results = {"processed": 0, "skipped": 0, "failed": 0}

    for file_path in file_paths:
        print(f"\n{'='*60}")
        print(f"Processing: {file_path.name}")
        print(f"{'='*60}")

        try:
            result = embedder.process_document(
                file_path=str(file_path),
                table_name=table_name,
                chunk_size=chunk_size,
                overlap=overlap,
                strategy=chunking_strategy,
                similarity_threshold=similarity_threshold,
                skip_if_exists=skip_if_exists
            )

            if result == "skipped":
                print(f"Status: SKIPPED (no changes)")
                results["skipped"] += 1
            else:
                print(f"Status: SUCCESS")
                results["processed"] += 1

        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found")
            results["failed"] += 1
        except Exception as e:
            print(f"Error during processing: {e}")
            results["failed"] += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Processed: {results['processed']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  Failed: {results['failed']}")
    print(f"{'='*60}")


def cmd_search(args):
    """Handle 'search' command - semantic search for similar chunks"""
    embedder = create_embedder_from_args(args)

    table_name = args.table or os.getenv("TABLE_NAME", "documents")
    limit = args.limit
    document_filter = args.document
    min_score = args.min_score

    # Validate min_score if provided
    if min_score is not None:
        if not 0.0 <= min_score <= 1.0:
            print(f"Error: --min-score must be between 0.0 and 1.0 (got {min_score})")
            sys.exit(1)

    # Get embedding for the query
    print(f"Searching for: '{args.query}'")
    if document_filter:
        print(f"Filtering by document: {document_filter}")
    if min_score is not None:
        print(f"Minimum score filter: {min_score:.2f}")
    print("Generating query embedding...")

    try:
        query_embedding = embedder.get_embedding(args.query)

        # Search for similar chunks
        print(f"Searching in table '{table_name}'...")
        results = embedder.storage.search_similar_chunks(
            query_embedding=query_embedding,
            table_name=table_name,
            limit=limit,
            document_name=document_filter,
            min_score=min_score
        )

        if not results:
            print("\nNo results found.")
            if document_filter:
                print(f"Tip: Check that document '{document_filter}' exists using 'python cli.py status'")
            if min_score is not None:
                print(f"Tip: Try lowering the --min-score threshold (current: {min_score:.2f})")
            return

        # Display results
        print(f"\nFound {len(results)} similar chunks:\n")

        for i, result in enumerate(results, 1):
            print(f"{'='*60}")
            print(f"Result {i} (Score: {result.get('similarity_score', 0):.4f})")
            print(f"{'='*60}")
            print(f"Document: {result['document_name']}")
            print(f"Chunk: {result['chunk_index']}")
            print(f"Content preview:")

            # Show first 300 characters of content
            content = result['content']
            preview = content[:300] + "..." if len(content) > 300 else content
            print(f"{preview}\n")

    except Exception as e:
        print(f"Error during search: {e}")
        sys.exit(1)


def cmd_status(args):
    """Handle 'status' command - show status of processed documents"""
    embedder = create_embedder_from_args(args)

    table_name = args.table or os.getenv("TABLE_NAME", "documents")

    print(f"Fetching document status from table '{table_name}'...\n")

    try:
        documents = embedder.storage.get_all_documents(table_name)

        if not documents:
            print("No documents found in the database.")
            return

        print(f"Total documents: {len(documents)}\n")
        print(f"{'Document Name':<40} {'Chunks':<10} {'Processed At':<25}")
        print(f"{'-'*75}")

        for doc in documents:
            doc_name = doc['document_name']
            chunk_count = doc['chunk_count']
            processed_at = doc['processed_at']

            # Truncate document name if too long
            if len(doc_name) > 37:
                doc_name = doc_name[:34] + "..."

            print(f"{doc_name:<40} {chunk_count:<10} {processed_at:<25}")

    except Exception as e:
        print(f"Error fetching status: {e}")
        sys.exit(1)


def cmd_delete(args):
    """Handle 'delete' command - delete a document and all its chunks"""
    embedder = create_embedder_from_args(args)

    table_name = args.table or os.getenv("TABLE_NAME", "documents")
    document_name = args.document_name

    print(f"Document to delete: {document_name}")
    print(f"Table: {table_name}")

    # Check if document exists first
    try:
        existing_hash = embedder.storage.check_document_exists(document_name, table_name)

        if not existing_hash:
            print(f"\n❌ Document '{document_name}' not found in table '{table_name}'.")
            print("\nTip: Use 'python cli.py status' to see all documents in the database.")
            sys.exit(1)

        # Confirm deletion
        if not args.force:
            print(f"\n⚠️  Warning: This will permanently delete all chunks for '{document_name}'")
            response = input("Are you sure you want to continue? (yes/no): ")

            if response.lower() not in ['yes', 'y']:
                print("Deletion cancelled.")
                return

        # Delete the document
        print(f"\nDeleting all chunks for '{document_name}'...")
        embedder.storage.delete_document_chunks(document_name, table_name)

        print(f"✅ Successfully deleted '{document_name}' and all its chunks from table '{table_name}'")

    except Exception as e:
        print(f"❌ Error deleting document: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Document Embedding Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Embed a single document
  python cli.py embed document.pdf

  # Embed multiple documents
  python cli.py embed doc1.pdf doc2.docx doc3.txt

  # Embed all documents in a directory
  python cli.py embed --directory ./documents

  # Force re-processing of documents
  python cli.py embed --force document.pdf

  # Search for similar chunks
  python cli.py search "What is Ansible?"

  # Show status of processed documents
  python cli.py status

  # Delete a document and all its chunks
  python cli.py delete document.pdf

  # Delete without confirmation prompt
  python cli.py delete --force document.pdf

  # Use custom settings
  python cli.py embed --chunk-size 500 --strategy paragraph document.pdf
        """
    )

    # Global arguments
    parser.add_argument('--lm-studio-url', help='LM Studio URL (default: from .env or http://localhost:1234/v1)')
    parser.add_argument('--table', help='Table name (default: from .env or "documents")')

    # PostgreSQL arguments
    parser.add_argument('--postgres-host', help='PostgreSQL host')
    parser.add_argument('--postgres-port', type=int, help='PostgreSQL port (default: 5432)')
    parser.add_argument('--postgres-db', help='PostgreSQL database name')
    parser.add_argument('--postgres-user', help='PostgreSQL username')
    parser.add_argument('--postgres-password', help='PostgreSQL password')
    parser.add_argument('--postgres-sslmode', help='PostgreSQL SSL mode (default: prefer)')

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # EMBED command
    embed_parser = subparsers.add_parser('embed', help='Process documents and generate embeddings')
    embed_parser.add_argument('files', nargs='*', help='Document file(s) to process')
    embed_parser.add_argument('-d', '--directory', help='Process all supported files in directory')
    embed_parser.add_argument('--chunk-size', type=int, help='Chunk size in characters')
    embed_parser.add_argument('--overlap', type=int, help='Overlap between chunks')
    embed_parser.add_argument('--strategy', choices=['character', 'paragraph', 'semantic'],
                             help='Chunking strategy (default: character)')
    embed_parser.add_argument('--similarity-threshold', type=float,
                             help='Similarity threshold for semantic chunking (0.0-1.0, default: 0.75)')
    embed_parser.add_argument('--force', action='store_true',
                             help='Force re-processing even if document unchanged')

    # SEARCH command
    search_parser = subparsers.add_parser('search', help='Search for similar chunks (semantic search)')
    search_parser.add_argument('query', help='Search query text')
    search_parser.add_argument('--limit', type=int, default=5, help='Number of results to return (default: 5)')
    search_parser.add_argument('--document', help='Filter results to specific document (e.g., "document.pdf")')
    search_parser.add_argument('--min-score', type=float, help='Minimum similarity score (0.0-1.0, e.g., 0.7)')

    # STATUS command
    status_parser = subparsers.add_parser('status', help='Show status of processed documents')

    # DELETE command
    delete_parser = subparsers.add_parser('delete', help='Delete a document and all its chunks')
    delete_parser.add_argument('document_name', help='Name of the document to delete (e.g., "document.pdf")')
    delete_parser.add_argument('--force', action='store_true',
                             help='Skip confirmation prompt')

    # Parse arguments
    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Dispatch to appropriate command handler
    if args.command == 'embed':
        if not args.files and not args.directory:
            embed_parser.error("Please provide file(s) or use --directory")
        cmd_embed(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'delete':
        cmd_delete(args)


if __name__ == "__main__":
    main()