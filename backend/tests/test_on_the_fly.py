"""Regression tests for on-the-fly round creation and hole-data persistence."""
import pytest
from httpx import AsyncClient

ON_THE_FLY = {
    "course_name": "Bærum Gul",
    "slope": 132,
    "course_rating": 69.7,
    "par_total": 71,
    "hcp_index": 18.4,
}


async def _start_round(client: AsyncClient, payload: dict | None = None) -> dict:
    resp = await client.post("/api/rounds", json=payload or ON_THE_FLY)
    assert resp.status_code == 200
    return resp.json()


# ── tee_id / course_id non-null ───────────────────────────────────────────────

async def test_on_the_fly_round_has_tee_id(client):
    data = await _start_round(client)
    assert data["tee_id"] is not None


async def test_on_the_fly_round_has_course_id(client):
    data = await _start_round(client)
    assert data["course_id"] is not None


# ── hole-data persistence ─────────────────────────────────────────────────────

async def test_score_with_hole_data_persists_to_local_holes(client):
    round_data = await _start_round(client)
    round_id = round_data["id"]
    tee_id = round_data["tee_id"]

    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1,
        "strokes": 4,
        "hole_par": 4,
        "hole_stroke_index": 7,
    })

    resp = await client.get(f"/api/courses/local/tees/{tee_id}/holes")
    assert resp.status_code == 200
    holes = resp.json()
    assert len(holes) == 1
    assert holes[0]["hole_number"] == 1
    assert holes[0]["par"] == 4
    assert holes[0]["stroke_index"] == 7


# ── club deduplication across rounds ─────────────────────────────────────────

async def test_two_rounds_same_course_name_reuse_club(client):
    payload = {
        "course_name": "Unique Course XYZ",
        "slope": 113,
        "course_rating": 72.0,
        "par_total": 72,
        "hcp_index": 10.0,
    }
    await _start_round(client, payload)
    await _start_round(client, payload)

    clubs_resp = await client.get("/api/courses")
    assert clubs_resp.status_code == 200
    clubs = clubs_resp.json()
    matching = [c for c in clubs if c["name"] == "Unique Course XYZ"]
    assert len(matching) == 1
