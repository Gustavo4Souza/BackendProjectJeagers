import os
import sys
from unittest.mock import AsyncMock, patch

# Must be set before any app module imports
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-eh-brewing"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
from fastapi.testclient import TestClient

from database import Base, engine, SessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except OSError:
        pass  # Windows may keep the file locked briefly after the session ends


@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe all rows before each test for isolation."""
    yield
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.ping = AsyncMock()
    mock.publish = AsyncMock(return_value=1)
    mock.aclose = AsyncMock()
    return mock


@pytest.fixture
def client(db, mock_redis):
    from main import app, get_db

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with patch("main.Redis") as MockRedis:
        MockRedis.from_url.return_value = mock_redis
        with TestClient(app, raise_server_exceptions=False) as c:
            app.state.redis = mock_redis
            yield c

    app.dependency_overrides.clear()
