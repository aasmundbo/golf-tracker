import pytest
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport
import database
from database import Base, get_db
from main import app

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
TEST_USERNAME = "admin"
TEST_PASSWORD = "testpass123"
TEST_PASSWORD_HASH = _pwd_ctx.hash(TEST_PASSWORD)


@pytest.fixture(autouse=True)
def patch_auth_settings(monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "admin_username", TEST_USERNAME)
    monkeypatch.setattr(config.settings, "admin_password_hash", TEST_PASSWORD_HASH)


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
    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    database.engine = original_engine
    await engine.dispose()


async def test_login_success(auth_client):
    resp = await auth_client.post("/api/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(auth_client):
    resp = await auth_client.post("/api/auth/login", json={
        "username": TEST_USERNAME,
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


async def test_login_wrong_username(auth_client):
    resp = await auth_client.post("/api/auth/login", json={
        "username": "notadmin",
        "password": TEST_PASSWORD,
    })
    assert resp.status_code == 401


async def test_protected_endpoint_without_token(auth_client):
    resp = await auth_client.get("/api/rounds")
    assert resp.status_code == 401


async def test_protected_endpoint_with_valid_token(auth_client):
    login_resp = await auth_client.post("/api/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    resp = await auth_client.get(
        "/api/rounds",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
