import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.api.dependencies import get_db
from app.api.dependencies_email import get_email_service
from app.db.base import Base
from app.main import app
from app.models.branch import Branch
from app.models.organization import Organization
from app.services.email.fake import FakeEmailService


@pytest.fixture
def email_service():
    return FakeEmailService()


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session, email_service: FakeEmailService):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = lambda: email_service

    with patch(
        "app.api.routes.auth.is_login_allowed",
        return_value=True,
    ):
        with patch(
            "app.api.routes.auth.is_login_ip_allowed",
            return_value=True,
        ):
            with TestClient(app) as test_client:
                yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def organization(db_session):
    organization = Organization(
        name="Test Organization",
        slug="test-organization",
    )
    db_session.add(organization)
    db_session.flush()
    return organization


@pytest.fixture
def branch(db_session, organization, region):
    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Test Branch",
        slug="test-branch",
    )
    db_session.add(branch)
    db_session.flush()
    return branch
