import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
import database
from database import Base, get_db
from main import app
from models.user import User, UserRole

_SAFE_JWT_SECRET = "test-secret-that-is-at-least-32-chars-for-validation-purposes"
FAKE_GOOGLE_SUB = "google-sub-12345"
FAKE_GOOGLE_EMAIL = "user@gmail.com"
FAKE_GOOGLE_PAYLOAD = {
    "sub": FAKE_GOOGLE_SUB,
    "email": FAKE_GOOGLE_EMAIL,
    "name": "Test User",
}


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "jwt_secret", _SAFE_JWT_SECRET)
    monkeypatch.setattr(config.settings, "google_client_id", "fake-client-id")
    monkeypatch.setattr(config.settings, "admin_username", "")
    monkeypatch.setattr(config.settings, "admin_password_hash", "")


@pytest.fixture
async def google_client():
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, TestSessionLocal

    app.dependency_overrides.clear()
    database.engine = original_engine
    database.AsyncSessionLocal = original_session_local
    await engine.dispose()


async def test_google_login_creates_new_user(google_client):
    client, SessionLocal = google_client
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_PAYLOAD):
        resp = await client.post("/api/auth/google", json={"id_token": "fake-token"})

    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"

    async with SessionLocal() as s:
        result = await s.execute(select(User).where(User.google_sub == FAKE_GOOGLE_SUB))
        user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == FAKE_GOOGLE_EMAIL
    assert user.name == "Test User"
    assert user.role == UserRole.user


async def test_google_login_existing_user_by_sub_does_not_duplicate(google_client):
    client, SessionLocal = google_client
    async with SessionLocal() as s:
        s.add(User(email=FAKE_GOOGLE_EMAIL, name="Old Name", google_sub=FAKE_GOOGLE_SUB, role=UserRole.user))
        await s.commit()

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_PAYLOAD):
        resp = await client.post("/api/auth/google", json={"id_token": "fake-token"})

    assert resp.status_code == 200

    async with SessionLocal() as s:
        result = await s.execute(select(User))
        users = result.scalars().all()
    assert len(users) == 1


async def test_google_login_links_google_sub_to_existing_email(google_client):
    client, SessionLocal = google_client
    async with SessionLocal() as s:
        s.add(User(email=FAKE_GOOGLE_EMAIL, name="Existing", google_sub=None, role=UserRole.user))
        await s.commit()

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=FAKE_GOOGLE_PAYLOAD):
        resp = await client.post("/api/auth/google", json={"id_token": "fake-token"})

    assert resp.status_code == 200

    async with SessionLocal() as s:
        result = await s.execute(select(User).where(User.email == FAKE_GOOGLE_EMAIL))
        user = result.scalar_one_or_none()
    assert user.google_sub == FAKE_GOOGLE_SUB


async def test_google_login_invalid_token_returns_401(google_client):
    client, _ = google_client
    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("bad token")):
        resp = await client.post("/api/auth/google", json={"id_token": "bad-token"})
    assert resp.status_code == 401
