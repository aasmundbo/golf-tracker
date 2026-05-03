import types
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
import database
from database import Base, get_db
from main import app
from auth import get_current_user, create_access_token
from models.user import User, UserRole
from models.course import LocalClub, LocalCourse
from models.round import Round

_SAFE_JWT_SECRET = "test-secret-that-is-at-least-32-chars-for-validation-purposes"


def _make_user_ns(**kwargs):
    defaults = dict(id=1, email="user@test.com", name="User", role=UserRole.user,
                    password_hash=None, google_sub=None, preferred_language="nb",
                    score_display="netto", default_hcp_index=None)
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_admin_ns(**kwargs):
    base = dict(id=1, email="admin@test.com", name="Admin", role=UserRole.admin)
    base.update(kwargs)
    return _make_user_ns(**base)


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "jwt_secret", _SAFE_JWT_SECRET)
    monkeypatch.setattr(config.settings, "admin_username", "")
    monkeypatch.setattr(config.settings, "admin_password_hash", "")


@pytest.fixture
async def users_client():
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


# ── GET /users/me ──────────────────────────────────────────────────────────────

async def test_get_me_returns_current_user(users_client):
    client, _ = users_client
    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=42, email="me@test.com", name="Me")

    resp = await client.get("/api/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@test.com"
    assert data["name"] == "Me"
    assert data["role"] == "user"
    assert "password_hash" not in data


async def test_get_me_unauthenticated(users_client):
    client, _ = users_client
    # remove override so real auth runs
    app.dependency_overrides.pop(get_current_user, None)
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


# ── PATCH /users/me ────────────────────────────────────────────────────────────

async def test_patch_me_updates_allowed_fields(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=10, email="patch@test.com", name="Old Name", role=UserRole.user)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=10, email="patch@test.com", name="Old Name")

    resp = await client.patch("/api/users/me", json={
        "name": "New Name",
        "preferred_language": "en",
        "default_hcp_index": 12.5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["preferred_language"] == "en"
    assert data["default_hcp_index"] == 12.5


async def test_patch_me_partial_update(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=11, email="partial@test.com", name="Original", preferred_language="nb", role=UserRole.user)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=11, email="partial@test.com", name="Original")

    resp = await client.patch("/api/users/me", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    assert resp.json()["preferred_language"] == "nb"  # unchanged


# ── GET /users (admin) ─────────────────────────────────────────────────────────

async def test_admin_list_users(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        s.add(User(email="a@test.com", name="A", role=UserRole.user))
        s.add(User(email="b@test.com", name="B", role=UserRole.admin))
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_admin_ns()

    resp = await client.get("/api/users")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_non_admin_cannot_list_users(users_client):
    client, _ = users_client
    app.dependency_overrides[get_current_user] = lambda: _make_user_ns()

    resp = await client.get("/api/users")
    assert resp.status_code == 403


# ── DELETE /users/{id} (admin) ─────────────────────────────────────────────────

async def test_admin_delete_user(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=20, email="todelete@test.com", name="Delete Me", role=UserRole.user)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_admin_ns(id=99)

    resp = await client.delete("/api/users/20")
    assert resp.status_code == 204

    async with SessionLocal() as s:
        result = await s.execute(select(User).where(User.id == 20))
        assert result.scalar_one_or_none() is None


async def test_admin_cannot_delete_self(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=30, email="admin@test.com", name="Admin", role=UserRole.admin)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_admin_ns(id=30)

    resp = await client.delete("/api/users/30")
    assert resp.status_code == 400


async def test_non_admin_cannot_delete_user(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=40, email="target@test.com", name="Target", role=UserRole.user)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=99)

    resp = await client.delete("/api/users/40")
    assert resp.status_code == 403


async def test_delete_nonexistent_user_returns_404(users_client):
    client, _ = users_client
    app.dependency_overrides[get_current_user] = lambda: _make_admin_ns()

    resp = await client.delete("/api/users/9999")
    assert resp.status_code == 404


# ── DELETE /users/me (self-delete) ─────────────────────────────────────────────

async def test_user_can_delete_own_account(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=50, email="selfdelete@test.com", name="Self Delete", role=UserRole.user)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=50)

    resp = await client.delete("/api/users/me")
    assert resp.status_code == 204

    async with SessionLocal() as s:
        result = await s.execute(select(User).where(User.id == 50))
        assert result.scalar_one_or_none() is None


async def test_admin_cannot_delete_own_account_via_me(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        admin = User(id=60, email="admindelete@test.com", name="Admin Delete", role=UserRole.admin)
        s.add(admin)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_admin_ns(id=60)

    resp = await client.delete("/api/users/me")
    assert resp.status_code == 400


async def test_delete_me_nullifies_created_by_on_clubs_and_courses(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=70, email="owner@test.com", name="Owner", role=UserRole.user)
        s.add(user)
        await s.flush()
        club = LocalClub(id=100, name="Owner's Club", created_by=70)
        course = LocalCourse(id=200, name="Owner's Course", created_by=70)
        s.add(club)
        s.add(course)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=70)

    resp = await client.delete("/api/users/me")
    assert resp.status_code == 204

    async with SessionLocal() as s:
        club_result = await s.execute(select(LocalClub).where(LocalClub.id == 100))
        club = club_result.scalar_one()
        assert club.created_by is None

        course_result = await s.execute(select(LocalCourse).where(LocalCourse.id == 200))
        course = course_result.scalar_one()
        assert course.created_by is None


# ── score_display field ────────────────────────────────────────────────────────

async def test_get_me_returns_score_display_default_netto(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=90, email="display@test.com", name="Display", role=UserRole.user)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=90, email="display@test.com", name="Display")

    resp = await client.get("/api/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["score_display"] == "netto"


async def test_patch_me_updates_score_display(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=91, email="displaypatch@test.com", name="Display Patch", role=UserRole.user)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=91, email="displaypatch@test.com", name="Display Patch")

    resp = await client.patch("/api/users/me", json={"score_display": "brutto"})
    assert resp.status_code == 200
    assert resp.json()["score_display"] == "brutto"


async def test_patch_me_rejects_invalid_score_display(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=92, email="displayinvalid@test.com", name="Display Invalid", role=UserRole.user)
        s.add(user)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=92, email="displayinvalid@test.com", name="Display Invalid")

    resp = await client.patch("/api/users/me", json={"score_display": "invalid"})
    assert resp.status_code == 422


async def test_delete_me_deletes_rounds(users_client):
    client, SessionLocal = users_client
    async with SessionLocal() as s:
        user = User(id=80, email="roundowner@test.com", name="Round Owner", role=UserRole.user)
        s.add(user)
        await s.flush()
        round_ = Round(id=300, user_id=80, course_source="local", club_name="Club", course_name="Course",
                       tee_name="Tee", slope=113.0, course_rating=72.0, par_total=72, hcp_index=10.0,
                       playing_handicap=10, status="finished")
        s.add(round_)
        await s.commit()

    app.dependency_overrides[get_current_user] = lambda: _make_user_ns(id=80)

    resp = await client.delete("/api/users/me")
    assert resp.status_code == 204

    async with SessionLocal() as s:
        result = await s.execute(select(Round).where(Round.id == 300))
        assert result.scalar_one_or_none() is None
