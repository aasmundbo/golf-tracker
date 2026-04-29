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


async def test_get_round_includes_scores(client):
    round_data = await _create_round(client, STANDARD_ROUND)
    round_id = round_data["id"]

    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 3, "strokes": 5, "hole_par": 4, "hole_stroke_index": 7,
    })

    resp = await client.get(f"/api/rounds/{round_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "scores" in body
    assert len(body["scores"]) == 1
    s = body["scores"][0]
    assert s["hole_number"] == 3
    assert s["strokes"] == 5
    assert s["hole_par"] == 4
    assert s["hole_stroke_index"] == 7


async def test_get_round_scores_empty_before_any_recorded(client):
    round_data = await _create_round(client, STANDARD_ROUND)
    round_id = round_data["id"]

    resp = await client.get(f"/api/rounds/{round_id}")
    assert resp.status_code == 200
    assert resp.json()["scores"] == []


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


# ── projected handicap differential ──────────────────────────────────────────

async def _setup_round_with_holes(client: AsyncClient) -> dict:
    """Create a local club/layout/tee with 18 holes (par 4, SI = hole number) and a round."""
    club = (await client.post("/api/courses", json={"name": "Test Club"})).json()
    layout = (await client.post(
        f"/api/courses/{club['id']}/layouts",
        json={"name": "Gul", "slope": 113.0, "course_rating": 72.0, "par_total": 72},
    )).json()
    tees = (await client.get(f"/api/courses/local/{layout['id']}/tees")).json()
    tee_id = tees[0]["id"]
    holes = [{"hole_number": h, "par": 4, "stroke_index": h} for h in range(1, 19)]
    await client.put(f"/api/courses/local/tees/{tee_id}/holes", json={"holes": holes})
    round_ = (await client.post("/api/rounds", json={
        "course_source": "local",
        "tee_id": tee_id,
        "course_name": "Test Course",
        "slope": 113.0,
        "course_rating": 72.0,
        "par_total": 72,
        "hcp_index": 18.0,
    })).json()
    return round_


async def test_projected_handicap_no_scores(client):
    # Slope=113, CR=72, playing_hcp=18; all par 4, SI 1-18 → each hole: projected = 4+1=5
    # adj_gross total = 18*5 = 90 → diff = (90-72)*113/113 = 18.0
    round_ = await _setup_round_with_holes(client)
    resp = await client.get(f"/api/rounds/{round_['id']}/projected_handicap")
    assert resp.status_code == 200
    body = resp.json()
    assert body["holes_played"] == 0
    assert body["projected_differential"] == pytest.approx(18.0, abs=0.05)
    assert len(body["hole_by_hole"]) == 18
    assert body["hole_by_hole"][0]["hole"] == 1
    assert body["hole_by_hole"][0]["projected_differential_after_hole"] == pytest.approx(18.0, abs=0.05)


async def test_projected_handicap_mid_round(client):
    # Holes 1-9 played with strokes=4 (par, vs projected 5 each)
    # adj total = 9*4 + 9*5 = 81 → diff = (81-72)*113/113 = 9.0
    round_ = await _setup_round_with_holes(client)
    for h in range(1, 10):
        await client.post(f"/api/rounds/{round_['id']}/scores", json={
            "hole_number": h, "strokes": 4, "hole_par": 4, "hole_stroke_index": h,
        })
    resp = await client.get(f"/api/rounds/{round_['id']}/projected_handicap")
    assert resp.status_code == 200
    body = resp.json()
    assert body["holes_played"] == 9
    assert body["projected_differential"] == pytest.approx(9.0, abs=0.05)
    assert len(body["hole_by_hole"]) == 18
    # After hole 1: 4 + 17*5 = 89 → 17.0
    assert body["hole_by_hole"][0]["projected_differential_after_hole"] == pytest.approx(17.0, abs=0.05)
    # After hole 9: 9*4 + 9*5 = 81 → 9.0
    assert body["hole_by_hole"][8]["hole"] == 9
    assert body["hole_by_hole"][8]["projected_differential_after_hole"] == pytest.approx(9.0, abs=0.05)


async def test_projected_handicap_requires_hole_data(client):
    # on_the_fly round: tee auto-created but no LocalHole records → can't project
    round_data = await _create_round(client, STANDARD_ROUND)
    resp = await client.get(f"/api/rounds/{round_data['id']}/projected_handicap")
    assert resp.status_code == 200
    assert resp.json()["projected_differential"] is None
