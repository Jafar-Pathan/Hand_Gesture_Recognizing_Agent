"""
pytest configuration and shared fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base, get_db
from backend.main import app

# ── In-memory SQLite test database ───────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///./test_gesture.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables once for the test session."""
    # Import models to register them with Base.metadata
    import backend.models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session():
    """Yield a clean database session per test (rolled back after)."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient with database dependency overridden."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client) -> dict:
    """Register a test user and return the token response."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture()
def auth_headers(client, registered_user) -> dict:
    """Log in and return Authorization headers."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client, db_session) -> dict:
    """Create an admin user and return Authorization headers."""
    from backend.core.security import hash_password
    from backend.models.user import User

    admin = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=hash_password("adminpass123"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
