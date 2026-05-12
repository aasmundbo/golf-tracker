import types
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport
import database
from database import Base, get_db
from main import app
from auth import get_current_user
from models.user import UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
_SAFE_JWT_SECRET = "test-secret-that-is-at-least-32-chars-for-validation-purposes"


def _mock_admin_user():
    return types.SimpleNamespace(
        id=1,
        email="admin@test.com",
        name="Admin",
        role=UserRole.admin,
        password_hash=None,
        google_sub=None,
        preferred_language="nb",
        score_display="netto",
        default_hcp_index=None,
        preferred_tee_gender=None,
        last_login_at=None,
    )


@pytest.fixture
async def client():
    # Patch jwt_secret before the lifespan runs its security check
    import config
    original_jwt_secret = config.settings.jwt_secret
    config.settings.jwt_secret = _SAFE_JWT_SECRET

    # StaticPool forces all connections to reuse the same underlying SQLite
    # connection, so tables created by create_all are visible to every session.
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch so lifespan's init_db() also targets the in-memory engine
    original_engine = database.engine
    database.engine = engine

    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    original_session_local = database.AsyncSessionLocal
    database.AsyncSessionLocal = TestSessionLocal

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    mock_user = _mock_admin_user()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    database.engine = original_engine
    database.AsyncSessionLocal = original_session_local
    config.settings.jwt_secret = original_jwt_secret
    await engine.dispose()
