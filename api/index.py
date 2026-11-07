"""Vercel Serverless Function entrypoint for MeetingMind FastAPI backend."""
import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent
_backend_dir = _root_dir / "backend"

if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

# Import the FastAPI application
from app.main import app  # noqa: E402

# Export app for Vercel ASGI runtime
__all__ = ["app"]
