#!/usr/bin/env python3
"""
Run Gunicorn for Render using Uvicorn workers.
This is the standard and most stable way to run FastAPI in production.
"""
import os
import sys

port = os.environ.get("PORT", "10000")
# We use UvicornWorker which is async-native and avoids "eventlet" issues.
sys.argv = [
    "gunicorn",
    "--bind", f"0.0.0.0:{port}",
    "--worker-class", "uvicorn.workers.UvicornWorker",
    "-w", "1",
    "--timeout", "120",
    "tracker_service.api:app",
]

from gunicorn.app.wsgiapp import run
if __name__ == "__main__":
    run()
