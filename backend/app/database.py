import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_db_url = _settings.database_url

# Translate legacy postgres:// scheme to postgresql:// for SQLAlchemy
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

_connect_args = {}
_engine_kwargs = {}

if _db_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False
    if _db_url.startswith("sqlite:///"):
        path_str = _db_url.replace("sqlite:///", "", 1)
        p = Path(path_str) if path_str.startswith("/") else Path(path_str).resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
elif _db_url.startswith("postgresql"):
    _engine_kwargs["pool_pre_ping"] = True
    # Serverless database optimization: NullPool avoids connection exhaustion on Supabase
    if os.getenv("VERCEL") or os.getenv("SERVERLESS"):
        _engine_kwargs["poolclass"] = NullPool
    else:
        _engine_kwargs["pool_recycle"] = 300

engine = create_engine(_db_url, connect_args=_connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Reliable initialisation: create all tables if they do not exist."""
    from . import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
