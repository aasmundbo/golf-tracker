"""Tests for round ownership enforcement (Task 5)."""
import types
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from main import app
from auth import get_current_user
from models.user import User, UserRole

ROUND_PAYLOAD = {
    "course_name": "Ownership Test Course",
    "slope": 113,
    "course_rating": 72.0,
    "par_total": 72,
    "hcp_index": 18.0,
}


def _make_user(id_: int, role: UserRole = UserRole.user):
    return types.SimpleNamespace(
        id=id_,
        email=f"user{id_}@test.com",
        name=f"User {id_}",
        role=role,
        password_hash=None,
        google_sub=None,
        preferred_language="nb",
        score_display="netto",
        default_hcp_index=None,
        preferred_tee_gender=None,
        last_login_at=None,
    )


_admin = _make_user(1, UserRole.admin)
_user2 = _make_user(2)
_user3 = _make_user(3)


async def test_create_round_stores_correct_user_id(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    resp = await client.post("/api/rounds", json=ROUND_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["user_id"] == 2


async def test_list_rounds_only_returns_own_rounds(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    await client.post("/api/rounds", json=ROUND_PAYLOAD)

    app.dependency_overrides[get_current_user] = lambda: _user3
    await client.post("/api/rounds", json=ROUND_PAYLOAD)

    # user2 only sees their own round
    app.dependency_overrides[get_current_user] = lambda: _user2
    rounds = (await client.get("/api/rounds")).json()
    assert len(rounds) == 1
    assert rounds[0]["user_id"] == 2

    # admin sees both
    app.dependency_overrides[get_current_user] = lambda: _admin
    all_rounds = (await client.get("/api/rounds")).json()
    assert len(all_rounds) == 2


async def test_get_round_forbidden_for_other_user(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    round_id = (await client.post("/api/rounds", json=ROUND_PAYLOAD)).json()["id"]

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.get(f"/api/rounds/{round_id}")
    assert resp.status_code == 403


async def test_admin_can_get_any_round(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    round_id = (await client.post("/api/rounds", json=ROUND_PAYLOAD)).json()["id"]

    app.dependency_overrides[get_current_user] = lambda: _admin
    resp = await client.get(f"/api/rounds/{round_id}")
    assert resp.status_code == 200


async def test_record_score_forbidden_for_other_user(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    round_id = (await client.post("/api/rounds", json=ROUND_PAYLOAD)).json()["id"]

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 4, "hole_par": 4, "hole_stroke_index": 1,
    })
    assert resp.status_code == 403


async def test_admin_can_filter_rounds_by_user_id(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    await client.post("/api/rounds", json=ROUND_PAYLOAD)

    app.dependency_overrides[get_current_user] = lambda: _user3
    await client.post("/api/rounds", json=ROUND_PAYLOAD)

    app.dependency_overrides[get_current_user] = lambda: _admin
    rounds = (await client.get("/api/rounds?user_id=2")).json()
    assert len(rounds) == 1
    assert rounds[0]["user_id"] == 2


async def test_non_admin_user_id_param_returns_403(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    await client.post("/api/rounds", json=ROUND_PAYLOAD)
    resp = await client.get("/api/rounds?user_id=3")
    assert resp.status_code == 403


async def test_hcp_update_forbidden_for_other_user(client):
    """PATCH /rounds/{id}/hcp returns 403 when round belongs to a different user."""
    app.dependency_overrides[get_current_user] = lambda: _user2
    round_id = (await client.post("/api/rounds", json=ROUND_PAYLOAD)).json()["id"]

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.patch(f"/api/rounds/{round_id}/hcp", json={"hcp_index": 5.0})
    assert resp.status_code == 403


async def test_hcp_update_allowed_for_round_owner(client):
    """PATCH /rounds/{id}/hcp succeeds for the round's own user."""
    app.dependency_overrides[get_current_user] = lambda: _user2
    round_id = (await client.post("/api/rounds", json=ROUND_PAYLOAD)).json()["id"]

    resp = await client.patch(f"/api/rounds/{round_id}/hcp", json={"hcp_index": 7.0})
    assert resp.status_code == 200
    assert resp.json()["hcp_index"] == 7.0


async def test_admin_list_rounds_includes_player_name(client):
    import database
    # Insert a real User row so the JOIN can resolve the name
    async with database.AsyncSessionLocal() as session:
        session.add(User(id=2, email="user2@test.com", name="User 2", role=UserRole.user))
        await session.commit()

    app.dependency_overrides[get_current_user] = lambda: _user2
    await client.post("/api/rounds", json=ROUND_PAYLOAD)

    app.dependency_overrides[get_current_user] = lambda: _admin
    rounds = (await client.get("/api/rounds")).json()
    assert "player_name" in rounds[0]
    user2_round = next(r for r in rounds if r["user_id"] == 2)
    assert user2_round["player_name"] == "User 2"
