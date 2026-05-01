from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db
from routers import courses, rounds, scores
from routers import auth as auth_router
from auth import get_current_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Golf Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth router is public — no get_current_user dependency
app.include_router(auth_router.router)

# All other routers require a valid JWT
_auth = [Depends(get_current_user)]
app.include_router(courses.router, dependencies=_auth)
app.include_router(rounds.router, dependencies=_auth)
app.include_router(scores.router, dependencies=_auth)

@app.get("/health")
async def health():
    return {"status": "ok"}
