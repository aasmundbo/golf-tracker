"""Tests for PATCH /api/rounds/{round_id}/hcp endpoint."""
import pytest
from httpx import AsyncClient

ROUND_PAYLOAD = {
    "course_name": "Test Course",
    "slope": 113,
    "course_rating": 72.0,
    "par_total": 72,
    "hcp_index": 18.0,
}


async def _create_round(client: AsyncClient, payload: dict = None) -> dict:
    resp = await client.post("/api/rounds", json=payload or ROUND_PAYLOAD)
    assert resp.status_code == 200
    return resp.json()


async def test_update_hcp_changes_hcp_index(client):
    """PATCH hcp updates hcp_index on the round."""
    round_data = await _create_round(client)
    round_id = round_data["id"]
    assert round_data["hcp_index"] == 18.0

    resp = await client.patch(f"/api/rounds/{round_id}/hcp", json={"hcp_index": 10.5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["hcp_index"] == 10.5


async def test_update_hcp_recalculates_playing_handicap(client):
    """PATCH hcp recalculates playing_handicap using slope/course_rating."""
    # slope=132, CR=69.7, par=71 → playing_hcp = round(18.4 * 132/113) = 21
    payload = {
        "course_name": "Bærum Gul",
        "slope": 132,
        "course_rating": 69.7,
        "par_total": 71,
        "hcp_index": 18.4,
    }
    round_data = await _create_round(client, payload)
    assert round_data["playing_handicap"] == 21

    # Change to hcp_index=9.0 → playing_hcp = round(9.0 * 132/113) = round(10.51) = 11
    resp = await client.patch(f"/api/rounds/{round_data['id']}/hcp", json={"hcp_index": 9.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["hcp_index"] == 9.0
    expected = round(9.0 * (132 / 113))
    assert data["playing_handicap"] == expected


async def test_update_hcp_returns_updated_round(client):
    """PATCH hcp returns full round with scores."""
    round_data = await _create_round(client)
    round_id = round_data["id"]

    # Add a score first
    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 5, "hole_par": 4, "hole_stroke_index": 1,
    })

    resp = await client.patch(f"/api/rounds/{round_id}/hcp", json={"hcp_index": 5.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["hcp_index"] == 5.0
    assert "scores" in data
    assert len(data["scores"]) == 1


async def test_update_hcp_missing_body_field(client):
    """PATCH hcp with missing hcp_index returns 422."""
    round_data = await _create_round(client)
    resp = await client.patch(f"/api/rounds/{round_data['id']}/hcp", json={})
    assert resp.status_code == 422


async def test_update_hcp_nonexistent_round(client):
    """PATCH hcp on non-existent round returns 404."""
    resp = await client.patch("/api/rounds/99999/hcp", json={"hcp_index": 10.0})
    assert resp.status_code == 404


async def test_update_hcp_finished_round_rejected(client):
    """PATCH hcp on a finished round returns 400."""
    round_data = await _create_round(client)
    round_id = round_data["id"]
    await client.put(f"/api/rounds/{round_id}/finish")

    resp = await client.patch(f"/api/rounds/{round_id}/hcp", json={"hcp_index": 10.0})
    assert resp.status_code == 400
