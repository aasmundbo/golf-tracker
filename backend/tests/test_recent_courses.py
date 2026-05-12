"""Tests for GET /api/rounds/recent-courses — per-user filtering and dedup."""
import types
import pytest
from httpx import AsyncClient
from main import app
from auth import get_current_user
from models.user import UserRole

def _make_user(id_: int):
    return types.SimpleNamespace(
        id=id_, email=f"user{id_}@test.com", name=f"User {id_}",
        role=UserRole.user, password_hash=None, google_sub=None,
        preferred_language="nb", score_display="netto",
        default_hcp_index=None, preferred_tee_gender=None, last_login_at=None,
    )

_user_a = _make_user(10)
_user_b = _make_user(11)


async def _create_round(client: AsyncClient, course_name: str, tee_name: str = "Default") -> dict:
    resp = await client.post("/api/rounds", json={
        "course_name": course_name,
        "tee_name": tee_name,
        "slope": 113,
        "course_rating": 72.0,
        "par_total": 72,
        "hcp_index": 10.0,
    })
    assert resp.status_code == 200
    return resp.json()


async def test_recent_courses_empty(client):
    """Returns empty list when user has no rounds."""
    resp = await client.get("/api/rounds/recent-courses")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_recent_courses_returns_most_recent(client):
    """Returns the most recently played courses."""
    await _create_round(client, "Course A")
    await _create_round(client, "Course B")

    resp = await client.get("/api/rounds/recent-courses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 2
    course_names = [d["course_name"] for d in data]
    assert "Course B" in course_names


async def test_recent_courses_deduplicates_same_course(client):
    """Playing the same course twice only counts once."""
    await _create_round(client, "Repeated Course", "Yellow")
    await _create_round(client, "Repeated Course", "Yellow")
    await _create_round(client, "Other Course", "Blue")

    resp = await client.get("/api/rounds/recent-courses")
    assert resp.status_code == 200
    data = resp.json()
    # Should be 2 distinct entries: Repeated Course + Other Course
    assert len(data) == 2
    course_names = [d["course_name"] for d in data]
    assert course_names.count("Repeated Course") == 1


async def test_recent_courses_limited_to_two(client):
    """Returns at most 2 entries even with many distinct courses."""
    await _create_round(client, "Course A")
    await _create_round(client, "Course B")
    await _create_round(client, "Course C")

    resp = await client.get("/api/rounds/recent-courses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_recent_courses_returns_expected_fields(client):
    """Each entry contains the expected fields."""
    await _create_round(client, "Field Test Course", "Red")

    resp = await client.get("/api/rounds/recent-courses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    entry = data[0]
    assert "course_name" in entry
    assert "tee_name" in entry
    assert "slope" in entry
    assert "course_rating" in entry
    assert "par_total" in entry


async def test_recent_courses_isolated_per_user(client):
    """User A's recent courses do not appear in User B's results."""
    app.dependency_overrides[get_current_user] = lambda: _user_a
    await _create_round(client, "User A Course")

    app.dependency_overrides[get_current_user] = lambda: _user_b
    recent = (await client.get("/api/rounds/recent-courses")).json()
    course_names = [r["course_name"] for r in recent]
    assert "User A Course" not in course_names


async def test_recent_courses_shows_own_after_isolation(client):
    """User B sees their own courses, not User A's."""
    app.dependency_overrides[get_current_user] = lambda: _user_a
    await _create_round(client, "Only A Course")

    app.dependency_overrides[get_current_user] = lambda: _user_b
    await _create_round(client, "Only B Course")

    recent = (await client.get("/api/rounds/recent-courses")).json()
    course_names = [r["course_name"] for r in recent]
    assert "Only B Course" in course_names
    assert "Only A Course" not in course_names
