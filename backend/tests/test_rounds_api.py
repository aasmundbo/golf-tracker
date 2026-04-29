import pytest
from httpx import AsyncClient

BARUM_ROUND = {
    "course_name": "Bærum Gul",
    "slope": 132,
    "course_rating": 69.7,
    "par_total": 71,
    "hcp_index": 18.4,
}

STANDARD_ROUND = {
    "course_name": "Test Course",
    "slope": 113,
    "course_rating": 72.0,
    "par_total": 72,
    "hcp_index": 18.0,
}


async def _create_round(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post("/api/rounds", json=payload)
    assert resp.status_code == 200
    return resp.json()


# ── playing handicap ──────────────────────────────────────────────────────────

async def test_create_round_barum_playing_handicap(client):
    data = await _create_round(client, BARUM_ROUND)
    assert data["playing_handicap"] == 21


# ── record and correct score ──────────────────────────────────────────────────

async def test_record_score(client):
    round_data = await _create_round(client, STANDARD_ROUND)
    round_id = round_data["id"]

    resp = await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1,
        "strokes": 5,
        "hole_par": 4,
        "hole_stroke_index": 1,
    })
    assert resp.status_code == 200
    assert resp.json()["strokes"] == 5


async def test_correct_score(client):
    round_data = await _create_round(client, STANDARD_ROUND)
    round_id = round_data["id"]

    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 5, "hole_par": 4, "hole_stroke_index": 1,
    })

    resp = await client.put(f"/api/rounds/{round_id}/scores/1", json={"strokes": 4})
    assert resp.status_code == 200
    assert resp.json()["strokes"] == 4


# ── live stats ────────────────────────────────────────────────────────────────

async def test_live_stats_par_on_si1_with_hcp18_gives_minus_one_net(client):
    # STANDARD_ROUND: slope=113, CR=72, par=72, hcp=18.0 → playing_hcp=18
    round_data = await _create_round(client, STANDARD_ROUND)
    round_id = round_data["id"]
    assert round_data["playing_handicap"] == 18

    # Par on SI-1 hole: hcp_strokes=1, net = par - par - 1 = -1
    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 4, "hole_par": 4, "hole_stroke_index": 1,
    })

    resp = await client.get(f"/api/rounds/{round_id}/live")
    assert resp.status_code == 200
    assert resp.json()["net_to_par"] == -1


# ── finish round ──────────────────────────────────────────────────────────────

async def test_finish_round(client):
    round_data = await _create_round(client, STANDARD_ROUND)
    round_id = round_data["id"]

    resp = await client.put(f"/api/rounds/{round_id}/finish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "finished"


# ── delete round ──────────────────────────────────────────────────────────────

async def test_delete_round_returns_404_after(client):
    round_data = await _create_round(client, STANDARD_ROUND)
    round_id = round_data["id"]

    del_resp = await client.delete(f"/api/rounds/{round_id}")
    assert del_resp.status_code == 200

    get_resp = await client.get(f"/api/rounds/{round_id}")
    assert get_resp.status_code == 404


async def test_delete_round_cascades_scores(client):
    round_data = await _create_round(client, STANDARD_ROUND)
    round_id = round_data["id"]

    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 4, "hole_par": 4, "hole_stroke_index": 1,
    })

    # Delete succeeds even with child scores
    del_resp = await client.delete(f"/api/rounds/{round_id}")
    assert del_resp.status_code == 200

    # Round is gone
    assert (await client.get(f"/api/rounds/{round_id}")).status_code == 404
