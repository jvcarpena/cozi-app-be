from datetime import datetime, timezone
from decimal import Decimal

import bcrypt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

from core.models.base import Base
from core.models.guest import Guest
from core.models.guest_verification import GuestVerification
from core.models.organization import Organization
from core.models.resort import Resort, ResortStatusEnum
from core.services import auto_session
from core.tools.celery.celery_app import celery as celery_instance
from main import app

pytest_plugins = ("celery.contrib.pytest",)


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


@pytest.fixture(scope="session")
def rabbitmq_container():
    with RabbitMqContainer("rabbitmq:3.13") as rabbitmq:
        yield rabbitmq


@pytest.fixture(scope="session")
def configure_celery_for_tests(rabbitmq_container):
    host = rabbitmq_container.get_container_host_ip()
    port = rabbitmq_container.get_exposed_port(5672)

    broker_url = f"amqp://guest:guest@{host}:{port}/"

    celery_instance.conf.update(broker_url=broker_url)  # noqa


@pytest.fixture(scope="session")
def celery_app(configure_celery_for_tests):

    return celery_instance


@pytest.fixture(scope="session")
def celery_worker_parameters(configure_celery_for_tests):
    return {
        "queues": ("celery",),
        "concurrency": 1,
        "perform_ping_check": False,
    }


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
def fake_organization(db_session):
    db_session.add(
        organization := Organization(
            name="TEST_ORGANIZATION",
        )
    )

    db_session.commit()

    yield organization


@pytest.fixture
def resort(db_session, fake_organization):
    db_session.add(
        fake_resort := Resort(
            organization_id=fake_organization.id,
            name="TEST_RESORT",
            status=ResortStatusEnum.ACTIVE,
            description="TEST_RESORT_DESCRIPTION",
            base_price_per_night=Decimal(25000),
            base_price_per_day_use=Decimal(12000),
            currency="PHP",
            max_guests=25,
            num_bedrooms=4,
            num_bathrooms=5,
            address="TEST_RESORT_ADDRESS",
        )
    )

    db_session.commit()

    yield fake_resort
