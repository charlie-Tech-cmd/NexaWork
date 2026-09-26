import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.base import Base
from app.main import app
from unittest.mock import patch


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
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch(
        "app.api.routes.auth.is_login_allowed",
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
