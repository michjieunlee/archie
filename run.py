"""
Uvicorn server runner with configurable logging.

Usage:
    python run.py

Environment variables (set in .env file):
    DEBUG=true - Enable debug logging
    PORT=8000 - Set server port (default: 8000)
    HOST=127.0.0.1 - Set server host (default: 127.0.0.1)
"""

import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    import os

    # Load settings from .env file
    settings = get_settings()

    # Get configuration from environment or use defaults
    # Note: HOST and PORT can be overridden via environment variables
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))

    # Set log level based on DEBUG setting from .env
    log_level = "debug" if settings.debug else "info"

    print(f"Starting {settings.app_name} server...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Log Level: {log_level}")
    print(f"Debug Mode: {settings.debug}")
    print(f"Docs available at: http://{host}:{port}/docs")
    print(f"API available at: http://{host}:{port}/api")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level=log_level,
        access_log=True,
    )
