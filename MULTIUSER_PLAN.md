# Multi-User Plan

## Phase 1 — User Model & Auth Wiring

### Task 1: User model + admin seeding ✅
- [x] Create `backend/models/user.py` with `User` and `UserRole`
- [x] Export from `backend/models/__init__.py`
- [x] Seed admin user in lifespan startup (idempotent, skips if email exists)
- [x] Tests: `backend/tests/test_users.py` — 3 tests, all green

### Task 2: JWT sub → user ID, get_current_user returns User ORM
- [ ] `create_access_token(user_id: int)` sets `{"sub": str(user_id)}`
- [ ] `get_current_user` decodes JWT, fetches User by ID, raises 401 if not found
- [ ] `routers/auth.py` login looks up User by email from DB
- [ ] Update `conftest.py` mock to return User ORM object
- [ ] Tests: `backend/tests/test_auth.py`

## Phase 2 — (future)
