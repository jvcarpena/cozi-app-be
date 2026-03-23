import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from core.models.base import Base
from core.services import auto_session
from main import app


@pytest.fixture(autouse=False, scope="session")
def container_engine():
    """
    Starts a throwaway PostgreSQL 16 Docker container once for the entire test session.
    Patches the app's global engine to point at the container instead of the real database.
    Requires Docker to be running locally.
    """

    with PostgresContainer("postgres:16") as postgres:
        url = postgres.get_connection_url().replace("postgresql://", "postgresql+psycopg://")
        auto_session.engine = create_engine(url)
        yield auto_session.engine


@pytest.fixture(autouse=True)
def recreate_schema(container_engine):
    """
    Drops and recreates all tables before every test automatically.
    Ensures each test starts with a clean, empty schema to prevent data leaking between tests.
    """

    Base.metadata.drop_all(container_engine)
    Base.metadata.create_all(container_engine)


@pytest.fixture
def db_session(container_engine):
    """
    Provides a fresh SQLAlchemy Session per test.
    Use this for tests that need direct database access without going through the HTTP layer.
    """

    with Session(container_engine) as session:
        yield session


@pytest.fixture
def client(db_session):
    """
    Provides a TestClient wrapping the FastAPI app for HTTP-level integration tests.
    Depends on db_session to ensure the database is ready before handling requests.
    """

    with TestClient(app) as client:
        yield client
