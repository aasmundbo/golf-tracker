import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_start_round(client):
    resp = await client.post("/api/rounds", json={
        "course_name": "Test Bane",
        "slope": 113,
        "course_rating": 72.0,
        "par_total": 72,
        "hcp_index": 18.0,
        "course_source": "on_the_fly",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["course_name"] == "Test Bane"
    assert data["playing_handicap"] == 18
    assert data["status"] == "active"

@pytest.mark.asyncio
async def test_start_round_playing_hcp_calculated(client):
    # Bærum Golfklubb Gul: slope=132, CR=69.7, par=71, hcp=18.4 → WHS: round(20.19) = 20
    resp = await client.post("/api/rounds", json={
        "course_name": "Bærum",
        "slope": 132,
        "course_rating": 69.7,
        "par_total": 71,
        "hcp_index": 18.4,
        "course_source": "on_the_fly",
    })
    assert resp.status_code == 200
    assert resp.json()["playing_handicap"] == 20

@pytest.mark.asyncio
async def test_record_score(client):
    round_resp = await client.post("/api/rounds", json={
        "course_name": "T", "slope": 113, "course_rating": 72.0,
        "par_total": 72, "hcp_index": 10.0, "course_source": "on_the_fly"
    })
    round_id = round_resp.json()["id"]

    resp = await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 5, "hole_par": 4, "hole_stroke_index": 7
    })
    assert resp.status_code == 200
    assert resp.json()["strokes"] == 5

@pytest.mark.asyncio
async def test_correct_score(client):
    round_resp = await client.post("/api/rounds", json={
        "course_name": "T", "slope": 113, "course_rating": 72.0,
        "par_total": 72, "hcp_index": 10.0, "course_source": "on_the_fly"
    })
    round_id = round_resp.json()["id"]
    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 5, "hole_par": 4, "hole_stroke_index": 7
    })
    resp = await client.put(f"/api/rounds/{round_id}/scores/1", json={"strokes": 4})
    assert resp.status_code == 200
    assert resp.json()["strokes"] == 4

@pytest.mark.asyncio
async def test_live_stats(client):
    round_resp = await client.post("/api/rounds", json={
        "course_name": "T", "slope": 113, "course_rating": 72.0,
        "par_total": 72, "hcp_index": 18.0, "course_source": "on_the_fly"
    })
    round_id = round_resp.json()["id"]
    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 4, "hole_par": 4, "hole_stroke_index": 1
    })
    resp = await client.get(f"/api/rounds/{round_id}/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["holes_played"] == 1
    assert data["gross_to_par"] == 0  # par
    assert data["net_to_par"] == -1   # got 1 hcp stroke on SI 1

@pytest.mark.asyncio
async def test_finish_round(client):
    round_resp = await client.post("/api/rounds", json={
        "course_name": "T", "slope": 113, "course_rating": 72.0,
        "par_total": 72, "hcp_index": 10.0, "course_source": "on_the_fly"
    })
    round_id = round_resp.json()["id"]
    resp = await client.put(f"/api/rounds/{round_id}/finish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "finished"

@pytest.mark.asyncio
async def test_delete_round(client):
    round_resp = await client.post("/api/rounds", json={
        "course_name": "T", "slope": 113, "course_rating": 72.0,
        "par_total": 72, "hcp_index": 10.0, "course_source": "on_the_fly"
    })
    round_id = round_resp.json()["id"]
    del_resp = await client.delete(f"/api/rounds/{round_id}")
    assert del_resp.status_code == 200
    get_resp = await client.get(f"/api/rounds/{round_id}")
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_round_cascades_scores(client):
    round_resp = await client.post("/api/rounds", json={
        "course_name": "T", "slope": 113, "course_rating": 72.0,
        "par_total": 72, "hcp_index": 10.0, "course_source": "on_the_fly"
    })
    round_id = round_resp.json()["id"]
    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 1, "strokes": 4, "hole_par": 4, "hole_stroke_index": 1
    })
    await client.delete(f"/api/rounds/{round_id}")
    assert (await client.get(f"/api/rounds/{round_id}")).status_code == 404
