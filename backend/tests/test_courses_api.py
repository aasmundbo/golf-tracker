import pytest
from httpx import AsyncClient


async def _create_club(client: AsyncClient, name: str = "Test Club") -> dict:
    resp = await client.post("/api/courses", json={"name": name})
    assert resp.status_code == 200
    return resp.json()


# ── create course (club) ──────────────────────────────────────────────────────

async def test_create_course(client):
    data = await _create_club(client, "Bærum GK")
    assert data["name"] == "Bærum GK"
    assert "id" in data


# ── create layout under course ────────────────────────────────────────────────

async def test_create_layout_under_course(client):
    club = await _create_club(client)
    resp = await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Gul",
        "slope": 132.0,
        "course_rating": 69.7,
        "par_total": 71,
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Gul"


# ── list layouts ──────────────────────────────────────────────────────────────

async def test_list_layouts(client):
    club = await _create_club(client)
    cid = club["id"]

    await client.post(f"/api/courses/{cid}/layouts", json={"name": "Gul"})
    await client.post(f"/api/courses/{cid}/layouts", json={"name": "Hvit"})

    resp = await client.get(f"/api/courses/{cid}/layouts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── delete course ─────────────────────────────────────────────────────────────

async def test_delete_course(client):
    club = await _create_club(client)
    cid = club["id"]

    del_resp = await client.delete(f"/api/courses/{cid}")
    assert del_resp.status_code == 200

    get_resp = await client.get(f"/api/courses/{cid}")
    assert get_resp.status_code == 404


async def test_delete_course_cascades_layouts_tees_and_holes(client):
    club = await _create_club(client, "Losby GK")
    cid = club["id"]

    layout_resp = await client.post(f"/api/courses/{cid}/layouts", json={
        "name": "Hvit",
        "slope": 128.0,
        "course_rating": 71.2,
        "par_total": 72,
    })
    assert layout_resp.status_code == 200
    layout_id = layout_resp.json()["id"]

    tees_resp = await client.get(f"/api/courses/local/{layout_id}/tees")
    tee_id = tees_resp.json()[0]["id"]

    await client.post(
        f"/api/courses/local/{layout_id}/tees/{tee_id}/holes",
        json={"hole_number": 1, "par": 4, "stroke_index": 7},
    )

    del_resp = await client.delete(f"/api/courses/{cid}")
    assert del_resp.status_code == 200

    assert (await client.get(f"/api/courses/{cid}")).status_code == 404
    assert (await client.get(f"/api/courses/{cid}/layouts")).json() == []
    assert (await client.get(f"/api/courses/local/tees/{tee_id}/holes")).json() == []


# ── search returns local results ──────────────────────────────────────────────

async def test_search_returns_local_results(client):
    club = await _create_club(client, "Bærum GK")
    await client.post(f"/api/courses/{club['id']}/layouts", json={"name": "Gul"})

    resp = await client.get("/api/courses/search", params={"q": "Bærum"})
    assert resp.status_code == 200

    results = resp.json()
    local = [r for r in results if r["source"] == "local"]
    assert len(local) > 0
    assert any(r["club_name"] == "Bærum GK" for r in local)
