import types
import pytest
from httpx import AsyncClient
from main import app
from auth import get_current_user
from models.user import UserRole


def _make_user(id_: int, role: UserRole = UserRole.user):
    return types.SimpleNamespace(
        id=id_,
        email=f"user{id_}@test.com",
        name=f"User {id_}",
        role=role,
        password_hash=None,
        google_sub=None,
        preferred_language="nb",
        default_hcp_index=None,
    )


_admin = _make_user(1, UserRole.admin)
_user2 = _make_user(2)
_user3 = _make_user(3)


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


# ── tee name when creating layouts ───────────────────────────────────────────

async def test_create_layout_with_custom_tee_name(client):
    club = await _create_club(client)
    resp = await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Hauptbane",
        "tee_name": "hvit",
        "slope": 130.0,
        "course_rating": 70.5,
        "par_total": 72,
    })
    assert resp.status_code == 200
    layout_id = resp.json()["id"]

    tees = (await client.get(f"/api/courses/local/{layout_id}/tees")).json()
    assert len(tees) == 1
    assert tees[0]["name"] == "hvit"


async def test_create_layout_default_tee_name_is_gul(client):
    club = await _create_club(client)
    resp = await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Hauptbane",
        "slope": 128.0,
        "course_rating": 69.0,
        "par_total": 71,
    })
    assert resp.status_code == 200
    layout_id = resp.json()["id"]

    tees = (await client.get(f"/api/courses/local/{layout_id}/tees")).json()
    assert len(tees) == 1
    assert tees[0]["name"] == "Gul"


# ── bulk upsert holes (PUT /local/tees/{tee_id}/holes) ───────────────────────

async def test_bulk_upsert_holes(client):
    club = await _create_club(client, "Hole Club")
    layout_resp = await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Bane",
        "slope": 120.0,
        "course_rating": 68.0,
        "par_total": 72,
    })
    layout_id = layout_resp.json()["id"]
    tee_id = (await client.get(f"/api/courses/local/{layout_id}/tees")).json()[0]["id"]

    holes_payload = {"holes": [
        {"hole_number": i, "par": 4, "stroke_index": i} for i in range(1, 19)
    ]}
    resp = await client.put(f"/api/courses/local/tees/{tee_id}/holes", json=holes_payload)
    assert resp.status_code == 200
    result = resp.json()
    assert len(result) == 18
    assert result[0]["hole_number"] == 1
    assert result[0]["par"] == 4

    # update a hole and verify
    holes_payload["holes"][0]["par"] = 5
    resp2 = await client.put(f"/api/courses/local/tees/{tee_id}/holes", json=holes_payload)
    assert resp2.status_code == 200
    updated = next(h for h in resp2.json() if h["hole_number"] == 1)
    assert updated["par"] == 5


async def test_bulk_upsert_holes_404_on_unknown_tee(client):
    resp = await client.put("/api/courses/local/tees/99999/holes", json={"holes": []})
    assert resp.status_code == 404


# ── search returns local results ──────────────────────────────────────────────

async def test_update_tee_flat(client):
    club = await _create_club(client, "Tee Update Club")
    layout_resp = await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Bane",
        "slope": 120.0,
        "course_rating": 68.0,
        "par_total": 72,
    })
    layout_id = layout_resp.json()["id"]
    tee_id = (await client.get(f"/api/courses/local/{layout_id}/tees")).json()[0]["id"]

    resp = await client.put(f"/api/courses/local/tees/{tee_id}", json={
        "name": "Rød",
        "slope": 135.0,
        "course_rating": 71.5,
        "par_total": 71,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Rød"
    assert data["slope"] == 135.0
    assert data["course_rating"] == 71.5
    assert data["par_total"] == 71


async def test_update_tee_flat_404(client):
    resp = await client.put("/api/courses/local/tees/99999", json={"name": "X"})
    assert resp.status_code == 404


async def test_duplicate_tee(client):
    club = await _create_club(client, "Dup Club")
    layout_resp = await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Bane",
        "slope": 125.0,
        "course_rating": 69.0,
        "par_total": 72,
    })
    layout_id = layout_resp.json()["id"]
    tee_id = (await client.get(f"/api/courses/local/{layout_id}/tees")).json()[0]["id"]

    holes_payload = {"holes": [
        {"hole_number": i, "par": 4 if i % 3 != 0 else 3, "stroke_index": i}
        for i in range(1, 19)
    ]}
    await client.put(f"/api/courses/local/tees/{tee_id}/holes", json=holes_payload)

    dup_resp = await client.post(f"/api/courses/local/tees/{tee_id}/duplicate")
    assert dup_resp.status_code == 200
    dup = dup_resp.json()

    assert dup["name"] == "Gul (kopi)"
    assert dup["slope"] == 125.0
    assert dup["course_rating"] == 69.0
    assert dup["par_total"] == 72
    assert dup["id"] != tee_id

    dup_holes = (await client.get(f"/api/courses/local/tees/{dup['id']}/holes")).json()
    assert len(dup_holes) == 18
    assert dup_holes[0]["par"] == holes_payload["holes"][0]["par"]
    assert dup_holes[0]["stroke_index"] == 1


async def test_duplicate_tee_404(client):
    resp = await client.post("/api/courses/local/tees/99999/duplicate")
    assert resp.status_code == 404


async def test_delete_tee(client):
    club = await _create_club(client, "Delete Tee Club")
    layout_resp = await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Bane",
        "slope": 120.0,
        "course_rating": 68.0,
        "par_total": 72,
    })
    layout_id = layout_resp.json()["id"]
    tee_id = (await client.get(f"/api/courses/local/{layout_id}/tees")).json()[0]["id"]

    del_resp = await client.delete(f"/api/courses/local/tees/{tee_id}")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"ok": True}

    tees = (await client.get(f"/api/courses/local/{layout_id}/tees")).json()
    assert all(t["id"] != tee_id for t in tees)


async def test_delete_tee_404(client):
    resp = await client.delete("/api/courses/local/tees/99999")
    assert resp.status_code == 404


async def test_search_returns_local_results(client):
    club = await _create_club(client, "Bærum GK")
    await client.post(f"/api/courses/{club['id']}/layouts", json={"name": "Gul"})

    resp = await client.get("/api/courses/search", params={"q": "Bærum"})
    assert resp.status_code == 200

    results = resp.json()
    local = [r for r in results if r["source"] == "local"]
    assert len(local) > 0
    assert any(r["club_name"] == "Bærum GK" for r in local)


# ── club delete ownership ─────────────────────────────────────────────────────

async def test_user_can_delete_own_club(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()

    resp = await client.delete(f"/api/courses/{club['id']}")
    assert resp.status_code == 200


async def test_user_cannot_delete_other_users_club(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.delete(f"/api/courses/{club['id']}")
    assert resp.status_code == 403


async def test_admin_can_delete_any_club(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()

    app.dependency_overrides[get_current_user] = lambda: _admin
    resp = await client.delete(f"/api/courses/{club['id']}")
    assert resp.status_code == 200


# ── club update ownership ─────────────────────────────────────────────────────

async def test_user_can_update_own_club(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()

    resp = await client.put(f"/api/courses/{club['id']}", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


async def test_user_cannot_update_other_users_club(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.put(f"/api/courses/{club['id']}", json={"name": "Hijacked"})
    assert resp.status_code == 403


async def test_admin_can_update_any_club(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()

    app.dependency_overrides[get_current_user] = lambda: _admin
    resp = await client.put(f"/api/courses/{club['id']}", json={"name": "Admin Updated"})
    assert resp.status_code == 200


# ── layout delete ownership ───────────────────────────────────────────────────

async def test_user_can_delete_own_layout(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={"name": "Bane"})).json()

    resp = await client.delete(f"/api/courses/local/{layout['id']}")
    assert resp.status_code == 200


async def test_user_cannot_delete_other_users_layout(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={"name": "Bane"})).json()

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.delete(f"/api/courses/local/{layout['id']}")
    assert resp.status_code == 403


async def test_admin_can_delete_any_layout(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "User2 Club"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={"name": "Bane"})).json()

    app.dependency_overrides[get_current_user] = lambda: _admin
    resp = await client.delete(f"/api/courses/local/{layout['id']}")
    assert resp.status_code == 200


# ── layout update ownership ───────────────────────────────────────────────────

async def test_user_can_update_own_layout(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "Club"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={"name": "Bane"})).json()

    resp = await client.put(f"/api/courses/local/{layout['id']}", json={"name": "Updated Bane"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Bane"


async def test_user_cannot_update_other_users_layout(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "Club"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={"name": "Bane"})).json()

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.put(f"/api/courses/local/{layout['id']}", json={"name": "Hijacked"})
    assert resp.status_code == 403


async def test_admin_can_update_any_layout(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    club = (await client.post("/api/courses", json={"name": "Club"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={"name": "Bane"})).json()

    app.dependency_overrides[get_current_user] = lambda: _admin
    resp = await client.put(f"/api/courses/local/{layout['id']}", json={"name": "Admin Updated"})
    assert resp.status_code == 200


# ── tee delete ownership ──────────────────────────────────────────────────────

async def _create_club_layout_tee(client) -> tuple[dict, dict, int]:
    club = (await client.post("/api/courses", json={"name": "Ownership Club"})).json()
    layout = (await client.post(f"/api/courses/{club['id']}/layouts", json={
        "name": "Bane", "slope": 120.0, "course_rating": 68.0, "par_total": 72,
    })).json()
    tee_id = (await client.get(f"/api/courses/local/{layout['id']}/tees")).json()[0]["id"]
    return club, layout, tee_id


async def test_user_can_delete_own_tee(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, _, tee_id = await _create_club_layout_tee(client)

    resp = await client.delete(f"/api/courses/local/tees/{tee_id}")
    assert resp.status_code == 200


async def test_user_cannot_delete_other_users_tee(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, _, tee_id = await _create_club_layout_tee(client)

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.delete(f"/api/courses/local/tees/{tee_id}")
    assert resp.status_code == 403


async def test_admin_can_delete_any_tee(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, _, tee_id = await _create_club_layout_tee(client)

    app.dependency_overrides[get_current_user] = lambda: _admin
    resp = await client.delete(f"/api/courses/local/tees/{tee_id}")
    assert resp.status_code == 200


# ── tee update ownership ──────────────────────────────────────────────────────

async def test_user_can_update_own_tee(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, _, tee_id = await _create_club_layout_tee(client)

    resp = await client.put(f"/api/courses/local/tees/{tee_id}", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


async def test_user_cannot_update_other_users_tee(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, _, tee_id = await _create_club_layout_tee(client)

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.put(f"/api/courses/local/tees/{tee_id}", json={"name": "Hijacked"})
    assert resp.status_code == 403


async def test_admin_can_update_any_tee(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, _, tee_id = await _create_club_layout_tee(client)

    app.dependency_overrides[get_current_user] = lambda: _admin
    resp = await client.put(f"/api/courses/local/tees/{tee_id}", json={"name": "Admin Updated"})
    assert resp.status_code == 200


# ── nested tee update ownership (PUT /local/{layout_id}/tees/{tee_id}) ───────

async def test_user_cannot_update_other_users_tee_nested(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, layout, tee_id = await _create_club_layout_tee(client)

    app.dependency_overrides[get_current_user] = lambda: _user3
    resp = await client.put(f"/api/courses/local/{layout['id']}/tees/{tee_id}", json={"name": "Hijacked"})
    assert resp.status_code == 403


async def test_user_can_update_own_tee_nested(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, layout, tee_id = await _create_club_layout_tee(client)

    resp = await client.put(f"/api/courses/local/{layout['id']}/tees/{tee_id}", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


async def test_admin_can_update_any_tee_nested(client):
    app.dependency_overrides[get_current_user] = lambda: _user2
    _, layout, tee_id = await _create_club_layout_tee(client)

    app.dependency_overrides[get_current_user] = lambda: _admin
    resp = await client.put(f"/api/courses/local/{layout['id']}/tees/{tee_id}", json={"name": "Admin Updated"})
    assert resp.status_code == 200
