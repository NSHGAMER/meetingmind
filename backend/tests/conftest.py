import os

os.environ["DATABASE_URL"] = "sqlite://"  # set before app import
os.environ["JWT_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.database import Base, get_db
from app.deps import get_llm, get_memory
from app.main import app

from .fakes import FakeLLM, FakeMemory


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app import models  # noqa: F401

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    memory, llm = FakeMemory(), FakeLLM()
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_memory] = lambda: memory
    app.dependency_overrides[get_llm] = lambda: llm
    client = TestClient(app)
    yield type("Env", (), {"client": client, "memory": memory, "llm": llm, "Session": Session})
    app.dependency_overrides.clear()


def register(client, email="a@example.com", name="Alice"):
    r = client.post("/api/auth/register", json={"email": email, "name": name, "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(env):
    return register(env.client)
