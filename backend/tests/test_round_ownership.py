"""Tests for round ownership enforcement (Task 5)."""
import types
import pytest
from httpx import AsyncClient
from main import app
from auth import get_current_user
from models.user import UserRole

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
        default_hcp_index=None,
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
