# Multi-User Plan

## Phase 1 — User Model & Auth Wiring ✅ (complete, confirmed in production)

### Task 1: User model + admin seeding ✅
- [x] Create `backend/models/user.py` with `User` and `UserRole`
- [x] Export from `backend/models/__init__.py`
- [x] Seed admin user in lifespan startup (idempotent, skips if email exists)
- [x] Tests: `backend/tests/test_users.py` — 3 tests, all green

### Task 2: JWT sub → user ID, get_current_user returns User ORM ✅
- [x] `create_access_token(user_id: int)` sets `{"sub": str(user_id)}`
- [x] `get_current_user` decodes JWT, fetches User by ID, raises 401 if not found
- [x] `routers/auth.py` login looks up User by email from DB
- [x] Update `conftest.py` mock to return SimpleNamespace with User fields
- [x] Tests: `backend/tests/test_auth.py` — 5 tests, all green (62 total)

## Phase 2 — Round Ownership + Course Attribution ✅ (complete, confirmed in production)

### Task 3: Add nullable user_id to Round ✅
- [x] `Round.user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)`
- [x] `User` already imported before `Round` in `models/__init__.py`
- [x] Test: round created via API has `user_id=null`, no error

### Task 4: Backfill migration script ✅
- [x] `backend/migrations/backfill_user_id.py` — sets all NULL round user_ids to admin
- [x] Idempotent; handles empty DB (0 rows, no crash)
- [x] Ran in production: "Updated 0 rounds" — all existing rounds already had user_id set

### Task 5: Make user_id non-nullable + enforce ownership ✅
- [x] `Round.user_id` → `nullable=False`
- [x] `create_round` sets `user_id = current_user.id`
- [x] `list_rounds` filters by user_id (admin sees all)
- [x] `get_round`, `finish_round`, `delete_round`, `get_live_stats`, `get_projected_handicap`: ownership check → 403
- [x] `record_score`: ownership check → 403
- [x] Tests in `test_round_ownership.py` (5 tests)

### Task 6: created_by on LocalClub/LocalCourse, ownership on delete ✅
- [x] `LocalClub.created_by` and `LocalCourse.created_by` columns (nullable FK to users)
- [x] `create_course` / `create_layout` / `create_local_layout` set `created_by`
- [x] `delete_course` / `delete_local_layout`: 403 if not owner and not admin
- [x] Tests in `test_courses_api.py`

## Phase 2 Complete ✅
71 tests passing. All tasks committed and cherry-picked to `main`. Migration confirmed in production.

## Phase 3 — Google OAuth + Users CRUD

### Task 7: Google OAuth backend endpoint ✅
- [x] Add `google_client_id: str = ""` to `config.Settings`
- [x] `POST /api/auth/google` in `routers/auth.py` — accepts `{"id_token": "..."}`, verifies with `google.oauth2.id_token.verify_oauth2_token`, upserts User (google_sub → email fallback), issues JWT
- [x] Tests: `backend/tests/test_google_auth.py` — 4 tests, all green (75 total)

### Task 8: Users CRUD router ✅
- [x] `routers/users.py` with `GET /api/users/me`, `PATCH /api/users/me` (name, preferred_language, default_hcp_index)
- [x] Admin-only `GET /api/users` (list all), `DELETE /api/users/{id}` (with self-delete guard)
- [x] Registered in `main.py` under `_auth` dependencies
- [x] Tests: `backend/tests/test_users_router.py` — 10 tests, all green (85 total)

## Phase 3 Complete ✅
85 tests passing.
