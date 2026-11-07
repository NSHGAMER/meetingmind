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

            # On Vercel / Serverless, prioritize pure-Python pg8000 driver
            is_pg8000 = "pg8000" in db_url
            if (os.getenv("VERCEL") or os.getenv("SERVERLESS")) and not is_pg8000:
                try:
                    import pg8000  # noqa: F401
                    db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)
                    is_pg8000 = True
                except ImportError:
                    pass

            if is_pg8000:
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                connect_args["ssl_context"] = ctx
            else:
                if "sslmode" not in db_url and ("supabase" in db_url or os.getenv("VERCEL")):
                    connect_args["sslmode"] = "require"

        log.info("Initializing SQLAlchemy engine (type: %s)", db_url.split(":")[0])
        try:
            _engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
        except Exception as e:
            # Fallback to pure-Python pg8000 driver if psycopg2 has binary/shared-library issues on Vercel
            if ("psycopg" in str(e).lower() or "no module" in str(e).lower()) and db_url.startswith("postgresql://"):
                alt_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)
                log.warning("Postgres driver error (%s). Falling back to pure-Python pg8000: %s", e, alt_url.split("@")[-1])
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                _engine = create_engine(alt_url, connect_args={"ssl_context": ctx}, **engine_kwargs)
            else:
                raise
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
