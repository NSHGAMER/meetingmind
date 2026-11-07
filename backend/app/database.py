import logging
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from .config import get_settings

log = logging.getLogger("meetingmind.database")


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None
_db_initialized = False


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.database_url

        # Translate legacy postgres:// scheme to postgresql:// for SQLAlchemy
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        connect_args = {}
        engine_kwargs = {}

        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            if db_url.startswith("sqlite:///"):
                path_str = db_url.replace("sqlite:///", "", 1)
                # On serverless (Vercel / Lambda), filesystem is read-only except /tmp
                if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")) and not path_str.startswith("/tmp"):
                    db_url = "sqlite:////tmp/meetingmind.db"
                    path_str = "/tmp/meetingmind.db"
                p = Path(path_str) if path_str.startswith("/") else Path(path_str).resolve()
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
        elif db_url.startswith("postgresql"):
            engine_kwargs["pool_pre_ping"] = True
            # Serverless database optimization: NullPool avoids connection exhaustion on Supabase
            if os.getenv("VERCEL") or os.getenv("SERVERLESS"):
                engine_kwargs["poolclass"] = NullPool
            else:
                engine_kwargs["pool_recycle"] = 300

        log.info("Initializing SQLAlchemy engine (type: %s)", db_url.split(":")[0])
        _engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
    return _engine


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


def init_db() -> None:
    """Create all tables if they do not exist."""
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=get_engine())


def ensure_db_initialized() -> None:
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True


def get_db():
    ensure_db_initialized()
    session_factory = get_sessionmaker()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def __getattr__(name: str):
    if name == "engine":
        return get_engine()
    if name == "SessionLocal":
        return get_sessionmaker()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
