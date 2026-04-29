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


async def test_get_round_returns_tee_id(client):
    """GET /rounds/:id must include tee_id so ActiveRound can pre-load hole data."""
    club = (await client.post("/api/courses", json={"name": "Bærum GK"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "18 Hull", "slope": 127, "course_rating": 71.4, "par_total": 72,
    })).json()
    tees = (await client.get(f"/api/courses/local/{layout['id']}/tees")).json()
    tee_id = tees[0]["id"]

    round_data = (await client.post("/api/rounds", json={
        "course_source": "local", "club_name": "Bærum GK", "course_name": "18 Hull",
        "tee_id": tee_id, "slope": 127, "course_rating": 71.4, "par_total": 72, "hcp_index": 15.0,
    })).json()

    fetched = (await client.get(f"/api/rounds/{round_data['id']}")).json()
    assert fetched["tee_id"] == tee_id


async def test_hole_data_preloads_on_second_round(client):
    """Par/SI entered via HoleDataPrompt on round 1 is available for pre-load on round 2."""
    club = (await client.post("/api/courses", json={"name": "Fornebu GK"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Bane 1", "slope": 120, "course_rating": 70.0, "par_total": 72,
    })).json()
    tees = (await client.get(f"/api/courses/local/{layout['id']}/tees")).json()
    tee_id = tees[0]["id"]

    def _round_payload():
        return {
            "course_source": "local", "club_name": "Fornebu GK", "course_name": "Bane 1",
            "tee_id": tee_id, "slope": 120, "course_rating": 70.0, "par_total": 72, "hcp_index": 12.0,
        }

    # Round 1: user manually enters par/si (simulates HoleDataPrompt submission)
    r1 = (await client.post("/api/rounds", json=_round_payload())).json()
    await client.post(f"/api/rounds/{r1['id']}/scores", json={
        "hole_number": 1, "strokes": 5, "hole_par": 4, "hole_stroke_index": 7,
    })
    await client.post(f"/api/rounds/{r1['id']}/scores", json={
        "hole_number": 2, "strokes": 3, "hole_par": 3, "hole_stroke_index": 11,
    })

    # Round 2: hole data should be accessible without manual entry
    r2 = (await client.post("/api/rounds", json=_round_payload())).json()
    assert r2["tee_id"] == tee_id

    holes = (await client.get(f"/api/courses/local/tees/{tee_id}/holes")).json()
    assert len(holes) == 2
    h1 = next(h for h in holes if h["hole_number"] == 1)
    h2 = next(h for h in holes if h["hole_number"] == 2)
    assert h1["par"] == 4 and h1["stroke_index"] == 7
    assert h2["par"] == 3 and h2["stroke_index"] == 11


async def test_on_the_fly_reuses_layout_and_tee_across_rounds(client):
    """Two on-the-fly rounds for the same course share the same tee_id."""
    r1 = await _start_round(client)
    r2 = await _start_round(client)
    assert r1["tee_id"] == r2["tee_id"]
    assert r1["course_id"] == r2["course_id"]


async def test_on_the_fly_hole_data_available_second_round(client):
    """Par/SI entered via HoleDataPrompt on round 1 pre-loads without a prompt on round 2."""
    r1 = await _start_round(client)
    await client.post(f"/api/rounds/{r1['id']}/scores", json={
        "hole_number": 1, "strokes": 5, "hole_par": 4, "hole_stroke_index": 7,
    })
    await client.post(f"/api/rounds/{r1['id']}/scores", json={
        "hole_number": 2, "strokes": 3, "hole_par": 3, "hole_stroke_index": 11,
    })

    r2 = await _start_round(client)
    assert r2["tee_id"] == r1["tee_id"]

    holes = (await client.get(f"/api/courses/local/tees/{r2['tee_id']}/holes")).json()
    by_hole = {h["hole_number"]: h for h in holes}
    assert by_hole[1]["par"] == 4 and by_hole[1]["stroke_index"] == 7
    assert by_hole[2]["par"] == 3 and by_hole[2]["stroke_index"] == 11


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
