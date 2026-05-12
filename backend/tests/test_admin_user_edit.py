"""Tests for admin user editing and listing."""
import types
import pytest
from httpx import AsyncClient
from main import app
from auth import get_current_user
import database
from models.user import User, UserRole

_regular_user = types.SimpleNamespace(
    id=99, email="regular@test.com", name="Regular", role=UserRole.user,
    password_hash=None, google_sub=None, preferred_language="nb",
    score_display="netto", default_hcp_index=None,
    preferred_tee_gender=None, last_login_at=None,
)


async def _seed_user(name: str = "Test User", email: str = "test@example.com") -> int:
    """Insert a non-admin user directly into the test DB and return its id."""
    async with database.AsyncSessionLocal() as session:
        user = User(email=email, name=name, role=UserRole.user, preferred_language="nb", score_display="netto")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def test_admin_can_patch_user_name(client):
    """Admin can update a user's name via PATCH /api/users/{id}."""
    user_id = await _seed_user("Original Name", "patch@example.com")
    resp = await client.patch(f"/api/users/{user_id}", json={"name": "Updated Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


async def test_admin_can_patch_user_language(client):
    """Admin can update a user's preferred_language."""
    user_id = await _seed_user("Lang User", "lang@example.com")
    resp = await client.patch(f"/api/users/{user_id}", json={"preferred_language": "en"})
    assert resp.status_code == 200
    assert resp.json()["preferred_language"] == "en"


async def test_admin_can_patch_user_hcp(client):
    """Admin can update a user's default_hcp_index."""
    user_id = await _seed_user("Hcp User", "hcp@example.com")
    resp = await client.patch(f"/api/users/{user_id}", json={"default_hcp_index": 14.2})
    assert resp.status_code == 200
    assert resp.json()["default_hcp_index"] == pytest.approx(14.2)


async def test_admin_can_patch_user_score_display(client):
    """Admin can update a user's score_display preference."""
    user_id = await _seed_user("Score User", "score@example.com")
    resp = await client.patch(f"/api/users/{user_id}", json={"score_display": "brutto"})
    assert resp.status_code == 200
    assert resp.json()["score_display"] == "brutto"


async def test_patch_nonexistent_user_returns_404(client):
    """Patching a user that doesn't exist returns 404."""
    resp = await client.patch("/api/users/99999", json={"name": "Ghost"})
    assert resp.status_code == 404


async def test_list_users_includes_last_login_at(client):
    """GET /api/users returns last_login_at field for each user."""
    resp = await client.get("/api/users")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    for user in data:
        assert "last_login_at" in user


async def test_list_users_search(client):
    """GET /api/users?search=... returns matching users."""
    await _seed_user("Findable Person", "findable@example.com")
    resp = await client.get("/api/users?search=Findable")
    assert resp.status_code == 200
    data = resp.json()
    assert any(u["display_name"] == "Findable Person" for u in data)


async def test_non_admin_cannot_list_users(client):
    """Regular users cannot list all users."""
    app.dependency_overrides[get_current_user] = lambda: _regular_user
    resp = await client.get("/api/users")
    assert resp.status_code == 403


async def test_non_admin_cannot_patch_other_user(client):
    """Regular users cannot patch another user's settings."""
    user_id = await _seed_user("Target User", "target@example.com")
    app.dependency_overrides[get_current_user] = lambda: _regular_user
    resp = await client.patch(f"/api/users/{user_id}", json={"name": "Hacked"})
    assert resp.status_code == 403
