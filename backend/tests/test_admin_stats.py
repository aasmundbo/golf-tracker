"""Tests for GET /api/admin/stats endpoint."""
import types
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from models.round import Round
from models.user import User, UserRole
from datetime import datetime, timezone, timedelta
from main import app
from auth import get_current_user
import database

_regular_user = types.SimpleNamespace(
    id=99, email="regular@test.com", name="Regular", role=UserRole.user,
    password_hash=None, google_sub=None, preferred_language="nb",
    score_display="netto", default_hcp_index=None,
    preferred_tee_gender=None, last_login_at=None,
)


async def _get_session() -> AsyncSession:
    async with database.AsyncSessionLocal() as s:
        return s


async def _create_round(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post("/api/rounds", json=payload)
    assert resp.status_code == 200
    return resp.json()


async def test_admin_stats_empty_db(client):
    """Stats endpoint returns zeros when no data exists."""
    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rounds"] == 0
    assert data["total_users"] == 0
    assert data["avg_rounds_per_user"] == 0
    assert data["completion_rate"] == 0
    assert data["top_courses"] == []
    assert data["top_users"] == []
    assert data["rounds_by_source"] == {}
    assert data["inactive_users"] == 0


async def test_admin_stats_with_rounds(client):
    """Stats endpoint counts rounds and users correctly."""
    await _create_round(client, {
        "course_name": "Club A",
        "slope": 113,
        "course_rating": 72.0,
        "par_total": 72,
        "hcp_index": 10.0,
    })
    await _create_round(client, {
        "course_name": "Club B",
        "slope": 120,
        "course_rating": 71.0,
        "par_total": 72,
        "hcp_index": 12.0,
    })

    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rounds"] == 2


async def test_admin_stats_completion_rate(client):
    """completion_rate is percentage of finished rounds."""
    r1 = await _create_round(client, {
        "course_name": "Course", "slope": 113,
        "course_rating": 72.0, "par_total": 72, "hcp_index": 10.0,
    })
    r2 = await _create_round(client, {
        "course_name": "Course", "slope": 113,
        "course_rating": 72.0, "par_total": 72, "hcp_index": 10.0,
    })
    # Finish one
    await client.put(f"/api/rounds/{r1['id']}/finish")

    resp = await client.get("/api/admin/stats")
    data = resp.json()
    assert data["completion_rate"] == 50


async def test_admin_stats_top_courses(client):
    """top_courses lists most frequently played club+course+tee combos."""
    for _ in range(3):
        await _create_round(client, {
            "course_name": "Popular Course", "slope": 113,
            "course_rating": 72.0, "par_total": 72, "hcp_index": 10.0,
        })
    await _create_round(client, {
        "course_name": "Rare Course", "slope": 113,
        "course_rating": 72.0, "par_total": 72, "hcp_index": 10.0,
    })

    resp = await client.get("/api/admin/stats")
    data = resp.json()
    top = data["top_courses"]
    assert len(top) >= 1
    assert top[0]["count"] == 3
    assert top[0]["course_name"] == "Popular Course"


async def test_admin_stats_rounds_by_source(client):
    """rounds_by_source groups round counts by course_source."""
    await _create_round(client, {
        "course_source": "local",
        "course_name": "Club", "slope": 113,
        "course_rating": 72.0, "par_total": 72, "hcp_index": 10.0,
    })

    resp = await client.get("/api/admin/stats")
    data = resp.json()
    assert "rounds_by_source" in data
    sources = data["rounds_by_source"]
    assert isinstance(sources, dict)


async def test_admin_stats_forbidden_for_regular_user(client):
    """Non-admin users cannot access the stats endpoint."""
    app.dependency_overrides[get_current_user] = lambda: _regular_user
    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 403
