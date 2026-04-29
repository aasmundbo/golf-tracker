import pytest

@pytest.mark.asyncio
async def test_on_the_fly_auto_creates_club_and_course(client):
    resp = await client.post("/api/rounds", json={
        "course_name": "AutoBane", "slope": 115, "course_rating": 71.0,
        "par_total": 72, "hcp_index": 12.0, "course_source": "on_the_fly"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["tee_id"] is not None
    assert data["course_id"] is not None
    # A local club should now exist
    courses_resp = await client.get("/api/courses")
    assert any(c["name"] == "AutoBane" for c in courses_resp.json())

@pytest.mark.asyncio
async def test_on_the_fly_reuses_existing_club(client):
    """Two on-the-fly rounds at same course name should reuse the same club."""
    for _ in range(2):
        await client.post("/api/rounds", json={
            "course_name": "SammeBane", "slope": 115, "course_rating": 71.0,
            "par_total": 72, "hcp_index": 12.0, "course_source": "on_the_fly"
        })
    courses_resp = await client.get("/api/courses")
    same_bane = [c for c in courses_resp.json() if c["name"] == "SammeBane"]
    assert len(same_bane) == 1, "Should not create duplicate clubs"
