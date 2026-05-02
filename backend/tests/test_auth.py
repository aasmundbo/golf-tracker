import pytest
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport
import database
from database import Base, get_db
from main import app
from models.user import User, UserRole
from auth import create_access_token

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "testpass123"
TEST_PASSWORD_HASH = _pwd_ctx.hash(TEST_PASSWORD)

_SAFE_JWT_SECRET = "test-secret-that-is-at-least-32-chars-for-validation-purposes"


@pytest.fixture(autouse=True)
def patch_jwt_secret(monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "jwt_secret", _SAFE_JWT_SECRET)
    # Disable admin seeding so tests control the DB themselves
    monkeypatch.setattr(config.settings, "admin_username", "")
    monkeypatch.setattr(config.settings, "admin_password_hash", "")


@pytest.fixture
async def auth_client():
    """Client that does NOT bypass get_current_user — tests real auth behaviour."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    original_engine = database.engine
    database.engine = engine
    original_session_local = database.AsyncSessionLocal
    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    database.AsyncSessionLocal = TestSessionLocal

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Seed a test user
    async with TestSessionLocal() as s:
        s.add(User(
            email=TEST_EMAIL,
            name="Admin",
            password_hash=TEST_PASSWORD_HASH,
            role=UserRole.admin,
        ))
        await s.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    database.engine = original_engine
    database.AsyncSessionLocal = original_session_local
    await engine.dispose()


async def test_login_success(auth_client):
    resp = await auth_client.post("/api/auth/login", json={
        "username": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(auth_client):
    resp = await auth_client.post("/api/auth/login", json={
        "username": TEST_EMAIL,
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


async def test_login_unknown_email(auth_client):
    resp = await auth_client.post("/api/auth/login", json={
        "username": "nobody@example.com",
        "password": TEST_PASSWORD,
    })
    assert resp.status_code == 401


async def test_protected_endpoint_without_token(auth_client):
    resp = await auth_client.get("/api/rounds")
    assert resp.status_code == 401


async def test_protected_endpoint_nonexistent_user_id(auth_client):
    # Token with a user_id that doesn't exist in the DB
    token = create_access_token(user_id=99999)
    resp = await auth_client.get(
        "/api/rounds",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
