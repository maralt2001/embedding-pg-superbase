#!/usr/bin/env python3
"""
Entry point for starting the web server
"""
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    # Get environment mode (development or production)
    environment = os.getenv("ENVIRONMENT", "development").lower()

    # Set defaults based on environment
    if environment == "production":
        default_host = "0.0.0.0"  # Accept connections from network
        default_reload = False
        default_workers = int(os.getenv("WEB_WORKERS", 4))
        log_level = "info"
    else:  # development
        default_host = "127.0.0.1"  # Localhost only
        default_reload = True
        default_workers = 1
        log_level = "debug"

    # Allow environment variables to override defaults
    port = int(os.getenv("WEB_PORT", 8000))
    host = os.getenv("WEB_HOST", default_host)
    reload = os.getenv("WEB_RELOAD", str(default_reload)).lower() == "true"
    workers = int(os.getenv("WEB_WORKERS", default_workers)) if not reload else 1

    print(f"Starting Document Embedding Pipeline Web Server...")
    print(f"  Environment: {environment}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Workers: {workers}")
    print(f"  Reload: {reload}")
    print(f"  Log Level: {log_level}")
    print(f"\nAccess the web interface at: http://{host}:{port}")

    if environment == "production":
        print("\n⚠️  Running in PRODUCTION mode")
        print("   - Auto-reload is disabled")
        print("   - Accepting connections from all network interfaces")
        print(f"   - Using {workers} worker processes")

    uvicorn.run(
        "backend.api.app:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level
    )
