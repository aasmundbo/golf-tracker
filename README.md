# Golf Tracker

A self-hosted golf round tracker with handicap calculation, Stableford scoring, and local course management.

## Features

- Search and add local courses manually
- Track hole-by-hole scores with +/- buttons during a round
- Live gross/net/Stableford stats as you play
- Playing handicap calculated from handicap index, slope, and course rating
- Round history

## Setup

```bash
cp .env.example .env
# Edit .env with your keys — see Authentication below for the auth vars
```

`.env` lives at `~/apps/golf-tracker/.env`. Full contents:

```
DATABASE_URL=sqlite:///./data/golf.db

ADMIN_USERNAME=your_username
ADMIN_PASSWORD_HASH=$$2b$$12$$...   # bcrypt hash — see Authentication below
JWT_SECRET=your_jwt_secret
```

## Authentication

The app uses a single admin user configured entirely via environment variables — no user database.

### Required env vars

| Variable | Description |
|---|---|
| `ADMIN_USERNAME` | The login username |
| `ADMIN_PASSWORD_HASH` | bcrypt hash of the password |
| `JWT_SECRET` | Secret used to sign JWT tokens |

### Generate the password hash

```bash
cd backend
python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
```

### Generate the JWT secret

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### `$` escaping in `.env` files

bcrypt hashes contain `$` characters (e.g. `$2b$12$abc...`). Docker Compose performs variable substitution on `.env` values, so every `$` must be doubled to `$$`:

```
# Wrong — Docker Compose will mangle the hash
ADMIN_PASSWORD_HASH=$2b$12$abc...

# Correct
ADMIN_PASSWORD_HASH=$$2b$$12$$abc...
```

## Running

Services are registered in `~/self-hosting/docker-compose.yml`. Launch from there:

```bash
cd ~/self-hosting
docker compose up -d golf-tracker-backend golf-tracker-frontend
```

Or restart after a code change:

```bash
docker compose up -d --build golf-tracker-backend golf-tracker-frontend
```

The app will be available at [golf-tracker.aasmundbo.com](http://golf-tracker.aasmundbo.com) once Traefik picks it up.

## Database

The SQLite database lives at `~/apps/golf-tracker/data/golf.db` on the host. It is bind-mounted into the container at `/app/data/golf.db` and contains:

- **clubs** — courses and their layouts
- **tees** — tee sets per layout (name, rating, slope, par)
- **holes** — hole-by-hole par and stroke index for each tee set
- **rounds** — round records (date, course, handicap index, playing handicap)
- **scores** — hole-by-hole gross scores per round

To wipe all data and start fresh:

```bash
cd ~/self-hosting
docker compose stop golf-tracker-backend golf-tracker-frontend
rm ~/apps/golf-tracker/data/golf.db
docker compose up -d golf-tracker-backend golf-tracker-frontend
```

## Project structure

```
backend/    FastAPI + SQLAlchemy (SQLite), uvicorn
frontend/   React + Vite + Tailwind, served by nginx with /api proxy to backend
data/       SQLite database (bind-mounted from ~/apps/golf-tracker/data/, not committed)
```
