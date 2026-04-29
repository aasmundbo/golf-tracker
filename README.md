# Golf Tracker

A self-hosted golf round tracker with handicap calculation, Stableford scoring, and course search via the GolfCourseAPI.

## Features

- Search courses via GolfCourseAPI or add local courses manually
- Track hole-by-hole scores with +/- buttons during a round
- Live gross/net/Stableford stats as you play
- Playing handicap calculated from handicap index, slope, and course rating
- Round history

## Getting a GolfCourseAPI key

1. Sign up at [golfcourseapi.com](https://golfcourseapi.com) — the free tier gives 300 requests/day
2. After signing in, copy your API key from the dashboard
3. Paste it into your `.env` file (see below)

## Setup

```bash
cp .env.example .env
# Edit .env and set your GOLF_COURSE_API_KEY
```

`.env` contents:

```
GOLF_COURSE_API_KEY=your_key_here
DATABASE_URL=sqlite:///./data/golf.db
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
