import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import database
from database import Base
from models.user import User, UserRole
from main import _seed_admin

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
_SAFE_JWT_SECRET = "test-secret-that-is-at-least-32-chars-for-validation-purposes"


@pytest.fixture
async def session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    original_engine = database.engine
    database.engine = engine
    TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    original_session_local = database.AsyncSessionLocal
    database.AsyncSessionLocal = TestSessionLocal

    async with TestSessionLocal() as s:
        yield s

    database.engine = original_engine
    database.AsyncSessionLocal = original_session_local
    await engine.dispose()


async def test_seed_admin_creates_user(session, monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "admin_username", "admin@example.com")
    monkeypatch.setattr(config.settings, "admin_password_hash", "$2b$12$fakehash")
    monkeypatch.setattr(config.settings, "jwt_secret", _SAFE_JWT_SECRET)

    await _seed_admin()

    result = await session.execute(select(User).where(User.email == "admin@example.com"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.role == UserRole.admin
    assert user.name == "Admin"


async def test_seed_admin_idempotent(session, monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "admin_username", "admin@example.com")
    monkeypatch.setattr(config.settings, "admin_password_hash", "$2b$12$fakehash")
    monkeypatch.setattr(config.settings, "jwt_secret", _SAFE_JWT_SECRET)

    await _seed_admin()
    await _seed_admin()

    result = await session.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1


async def test_duplicate_email_raises_integrity_error(session):
    u1 = User(email="dup@example.com", name="First", role=UserRole.user)
    u2 = User(email="dup@example.com", name="Second", role=UserRole.user)
    session.add(u1)
    await session.flush()
    session.add(u2)
    with pytest.raises(IntegrityError):
        await session.flush()
