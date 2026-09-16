"""PyInstaller entrypoint for the local Forma API sidecar."""

import argparse
import os
import uvicorn
from backend.app.main import app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forma local API sidecar")
    parser.add_argument("--host", default=os.getenv("FORMA_API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("FORMA_API_PORT", "8000")))
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
