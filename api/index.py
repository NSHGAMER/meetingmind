"""Vercel Serverless Function entrypoint for MeetingMind FastAPI backend."""
import logging
import os
import sys
import traceback
from pathlib import Path

log = logging.getLogger("meetingmind.vercel")

# Ensure api directory, backend directory, and root are in sys.path
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
backend_dir = root_dir / "backend"

for d in [str(current_dir), str(backend_dir), str(root_dir)]:
    if d not in sys.path:
        sys.path.insert(0, d)

try:
    from app.main import app

    @app.middleware("http")
    async def vercel_exception_middleware(request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            err_trace = traceback.format_exc()
            log.error("Unhandled error processing %s: %s\n%s", request.url.path, e, err_trace)
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error: {str(e)}",
                    "code": "internal_error",
                    "type": type(e).__name__,
                },
            )

except Exception as err:
    import_error_msg = str(err)
    err_trace = traceback.format_exc()
    log.critical("Failed to import MeetingMind FastAPI app:\n%s", err_trace)

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="MeetingMind Diagnostic Handler")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
    async def diagnostic_handler(path: str):
        safe_env = {
            k: v for k, v in os.environ.items()
            if not any(secret in k.lower() for secret in ["key", "secret", "pass", "token", "auth"])
        }
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend initialization failed",
                "detail": import_error_msg,
                "type": type(err).__name__,
                "traceback": err_trace,
                "sys_path": sys.path,
                "cwd": os.getcwd(),
                "available_env_vars": list(safe_env.keys()),
            },
        )

# Export app for Vercel ASGI runtime
__all__ = ["app"]
