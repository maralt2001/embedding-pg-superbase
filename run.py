#!/usr/bin/env python3
"""
Entry point for starting the web server
"""
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("WEB_PORT", 8000))
    host = os.getenv("WEB_HOST", "127.0.0.1")
    reload = os.getenv("WEB_RELOAD", "true").lower() == "true"

    print(f"Starting Document Embedding Pipeline Web Server...")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Reload: {reload}")
    print(f"\nAccess the web interface at: http://{host}:{port}")

    uvicorn.run(
        "backend.api.app:app",
        host=host,
        port=port,
        reload=reload
    )
