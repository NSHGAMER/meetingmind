"""Vercel Serverless Function entrypoint for MeetingMind FastAPI backend."""
import json
import logging
import os
import sys
import traceback
from pathlib import Path

log = logging.getLogger("meetingmind.vercel")

# Setup module search paths across all possible Vercel / Lambda folder layouts
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
backend_dir = root_dir / "backend"

candidates = [
    str(current_dir),
    str(current_dir / "app"),
    str(root_dir),
    str(backend_dir),
    str(root_dir / "api"),
]

for d in candidates:
    if d not in sys.path and os.path.exists(d):
        sys.path.insert(0, d)

_fastapi_app = None
_init_error = None
_init_traceback = None

try:
    try:
        from app.main import app as _candidate_app
    except ImportError:
        try:
            from api.app.main import app as _candidate_app
        except ImportError:
            from backend.app.main import app as _candidate_app
    _fastapi_app = _candidate_app
    log.info("Successfully loaded MeetingMind FastAPI app")
except Exception as err:
    _init_error = err
    _init_traceback = traceback.format_exc()
    sys.stderr.write(f"[MeetingMind Vercel Init Error] {err}\n{_init_traceback}\n")


async def app(scope, receive, send):
    """Universal ASGI handler for Vercel Serverless Python runtime."""
    scope_type = scope.get("type")

    # Handle ASGI lifespan events safely so the container never aborts startup
    if scope_type == "lifespan":
        while True:
            message = await receive()
            msg_type = message.get("type")
            if msg_type == "lifespan.startup":
                if _fastapi_app is not None:
                    try:
                        # Allow FastAPI lifespan to run if present
                        pass
                    except Exception as e:
                        sys.stderr.write(f"[Lifespan Startup Error] {e}\n")
                await send({"type": "lifespan.startup.complete"})
            elif msg_type == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    elif scope_type == "http":
        # If the app failed to initialize during import, return diagnostic JSON
        if _fastapi_app is None:
            safe_env = {
                k: v for k, v in os.environ.items()
                if not any(s in k.lower() for s in ["key", "secret", "pass", "token", "auth"])
            }
            error_payload = {
                "error": "Backend initialization failed",
                "detail": str(_init_error),
                "type": type(_init_error).__name__ if _init_error else "Unknown",
                "traceback": _init_traceback,
                "sys_path": sys.path,
                "cwd": os.getcwd(),
                "available_env_vars": list(safe_env.keys()),
            }
            body = json.dumps(error_payload, indent=2).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"access-control-allow-origin", b"*"),
                    (b"access-control-allow-methods", b"*"),
                    (b"access-control-allow-headers", b"*"),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            })
            return

        # FastAPI app is available - dispatch the HTTP request
        try:
            await _fastapi_app(scope, receive, send)
        except Exception as exc:
            err_str = str(exc)
            tb = traceback.format_exc()
            sys.stderr.write(f"[Unhandled Request Error] {err_str}\n{tb}\n")
            body = json.dumps({
                "error": "Internal server error",
                "detail": err_str,
                "type": type(exc).__name__,
            }).encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"access-control-allow-origin", b"*"),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
                "more_body": False,
            })


__all__ = ["app"]
