import pytest

@pytest.mark.asyncio
async def test_create_course(client):
    resp = await client.post("/api/courses", json={
        "name": "Bærum Golfklubb", "city": "Bærum", "country": "Norway"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Bærum Golfklubb"
    assert data["id"] is not None

@pytest.mark.asyncio
async def test_create_layout(client):
    course_resp = await client.post("/api/courses", json={"name": "Bærum Golfklubb"})
    course_id = course_resp.json()["id"]
    resp = await client.post(f"/api/courses/{course_id}/layouts", json={
        "name": "Hovedbane", "slope": 132, "course_rating": 69.7, "par_total": 71
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Hovedbane"
    assert data["id"] is not None

@pytest.mark.asyncio
async def test_list_layouts(client):
    course_resp = await client.post("/api/courses", json={"name": "Bærum Golfklubb"})
    course_id = course_resp.json()["id"]
    await client.post(f"/api/courses/{course_id}/layouts", json={"name": "Hovedbane", "slope": 132, "course_rating": 69.7, "par_total": 71})
    await client.post(f"/api/courses/{course_id}/layouts", json={"name": "Korthullsbane", "slope": 110, "course_rating": 60.0, "par_total": 54})
    resp = await client.get(f"/api/courses/{course_id}/layouts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

@pytest.mark.asyncio
async def test_delete_course(client):
    course_resp = await client.post("/api/courses", json={"name": "Slett meg"})
    course_id = course_resp.json()["id"]
    del_resp = await client.delete(f"/api/courses/{course_id}")
    assert del_resp.status_code == 200

@pytest.mark.asyncio
async def test_search_local_course(client):
    await client.post("/api/courses", json={"name": "Losby Golfklubb", "city": "Lørenskog"})
    resp = await client.get("/api/courses/search?q=Losby")
    assert resp.status_code == 200
    results = resp.json()
    local_results = [r for r in results if r["source"] == "local"]
    assert len(local_results) == 1
    assert "Losby" in local_results[0]["name"]

@pytest.mark.asyncio
async def test_hole_data_persisted_via_score(client):
    """Hole data entered during a round must persist to local_holes."""
    round_resp = await client.post("/api/rounds", json={
        "course_name": "Testbane", "slope": 120, "course_rating": 70.0,
        "par_total": 72, "hcp_index": 15.0, "course_source": "on_the_fly"
    })
    assert round_resp.status_code == 200
    round_data = round_resp.json()
    round_id = round_data["id"]
    tee_id = round_data.get("tee_id")
    assert tee_id is not None, "on_the_fly round must auto-create a tee"

    await client.post(f"/api/rounds/{round_id}/scores", json={
        "hole_number": 5, "strokes": 4, "hole_par": 4, "hole_stroke_index": 3
    })

    holes_resp = await client.get(f"/api/courses/local/tees/{tee_id}/holes")
    assert holes_resp.status_code == 200
    holes = holes_resp.json()
    hole5 = next((h for h in holes if h["hole_number"] == 5), None)
    assert hole5 is not None, "Hole 5 data should be persisted"
    assert hole5["par"] == 4
    assert hole5["stroke_index"] == 3
