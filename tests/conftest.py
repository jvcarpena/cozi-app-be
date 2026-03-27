from datetime import datetime, timezone, timedelta

import bcrypt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from core.models.base import Base
from core.models.guest import Guest
from core.models.guest_verification import GuestVerification
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
        url = postgres.get_connection_url(driver="psycopg")
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


@pytest.fixture
def guest(db_session):
    db_session.add(
        guest := Guest(
            id="guest",
            email_address="guest@gmail.com",
            hashed_password=bcrypt.hashpw("guest1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="verified",
            last_name="guest",
        )
    )

    db_session.add(
        GuestVerification(
            guest_id=guest.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
            verified_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()
    yield guest


@pytest.fixture
def unverified_guest(db_session):
    db_session.add(
        unverified_guest := Guest(
            id="unverified_guest",
            email_address="unverified_guest@gmail.com",
            hashed_password=bcrypt.hashpw("unverified1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="unverified",
            last_name="guest",
        )
    )

    db_session.add(
        GuestVerification(
            guest_id=unverified_guest.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()
    yield unverified_guest


@pytest.fixture
def unverified_guest_expired_link(db_session):
    db_session.add(
        unverified_guest_expired_link := Guest(
            id="unverified_guest_expired_link",
            email_address="unverified_guest_expired_link@gmail.com",
            hashed_password=bcrypt.hashpw("linkexpired1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="unverified guest",
            last_name="link expired",
        )
    )

    db_session.add(
        GuestVerification(
            guest_id=unverified_guest_expired_link.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc) - timedelta(hours=25),
        )
    )

    db_session.commit()
    yield unverified_guest_expired_link
