"""Regression tests for on-the-fly round creation, hole-data persistence, and local-tee pre-loading."""
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

# ── local-tee pre-load (regression: tee_id must survive round creation) ───────

async def test_local_tee_round_stores_tee_id(client):
    """Starting a round with an existing tee_id should preserve it on the round."""
    # Set up: club → course → tee → 2 holes
    club = (await client.post("/api/courses", json={"name": "Bærum GK"})).json()
    layout_resp = await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "18 Hull", "slope": 127, "course_rating": 71.4,
        "par_total": 72, "tee_name": "gul",
    })
    layout = layout_resp.json()
    tees = (await client.get(f"/api/courses/local/{layout['id']}/tees")).json()
    tee_id = tees[0]["id"]

    await client.post(f"/api/courses/local/{layout['id']}/tees/{tee_id}/holes",
                      json={"hole_number": 1, "par": 4, "stroke_index": 3})
    await client.post(f"/api/courses/local/{layout['id']}/tees/{tee_id}/holes",
                      json={"hole_number": 2, "par": 3, "stroke_index": 9})

    # Start a second round on the same course, passing tee_id explicitly
    round_data = (await client.post("/api/rounds", json={
        "course_source": "local",
        "club_name": "Bærum GK",
        "course_name": "18 Hull",
        "tee_name": "gul",
        "tee_id": tee_id,
        "slope": 127,
        "course_rating": 71.4,
        "par_total": 72,
        "hcp_index": 15.0,
    })).json()

    assert round_data["tee_id"] == tee_id

    # Holes must be accessible via the tee_id stored on the round
    holes = (await client.get(f"/api/courses/local/tees/{round_data['tee_id']}/holes")).json()
    assert len(holes) == 2
    assert holes[0]["par"] == 4
    assert holes[0]["stroke_index"] == 3
    assert holes[1]["par"] == 3
    assert holes[1]["stroke_index"] == 9


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
