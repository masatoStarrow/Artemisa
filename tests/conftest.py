"""
Shared test fixtures.
Uses SQLite async in-memory database for tests (no PostgreSQL needed).
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.infrastructure.database.connection import Base, get_db
from src.adapters.outbound.persistence.models.user_model import UserModel  # noqa: F401
from src.adapters.outbound.persistence.models.client_model import ClientModel  # noqa: F401


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Provide a test DB session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Provide an HTTPX AsyncClient with DB dependency overridden."""
    from main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Seed fixtures ────────────────────────────────────────────────────────

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SOPORTE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
COMERCIAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

INTERNAL_HEADERS_ADMIN = {
    "X-User-Id": str(ADMIN_ID),
    "X-User-Role": "admin",
    "X-Request-Id": "test-req-001",
}

INTERNAL_HEADERS_SOPORTE = {
    "X-User-Id": str(SOPORTE_ID),
    "X-User-Role": "soporte",
    "X-Request-Id": "test-req-002",
}

INTERNAL_HEADERS_COMERCIAL = {
    "X-User-Id": str(COMERCIAL_ID),
    "X-User-Role": "comercial",
    "X-Request-Id": "test-req-003",
}


@pytest_asyncio.fixture
async def seed_users(db_session: AsyncSession):
    """Create 3 seed users in the test DB."""
    now = datetime.now(timezone.utc)
    users = [
        UserModel(id=ADMIN_ID, email="admin@crm.com", full_name="Admin CRM", role="admin", created_at=now, updated_at=now),
        UserModel(id=SOPORTE_ID, email="soporte@crm.com", full_name="Agente Soporte", role="soporte", created_at=now, updated_at=now),
        UserModel(id=COMERCIAL_ID, email="comercial@crm.com", full_name="Agente Comercial", role="comercial", created_at=now, updated_at=now),
    ]
    for u in users:
        db_session.add(u)
    await db_session.commit()
    return users
