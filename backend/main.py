from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select
import database
from database import init_db
from routers import courses, rounds, scores, users as users_router
from routers import auth as auth_router
from auth import get_current_user
from config import settings
from limiter import limiter
from models.user import User, UserRole

_INSECURE_DEFAULT = "change-me-in-production-use-a-long-random-string"


async def _seed_admin():
    if not settings.admin_username or not settings.admin_password_hash:
        return
    async with database.AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == settings.admin_username))
        if existing.scalar_one_or_none() is not None:
            return
        admin = User(
            email=settings.admin_username,
            name="Admin",
            password_hash=settings.admin_password_hash,
            role=UserRole.admin,
        )
        session.add(admin)
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.jwt_secret == _INSECURE_DEFAULT or len(settings.jwt_secret) < 32:
        raise RuntimeError(
            "JWT_SECRET is insecure. Set a random string of at least 32 characters "
            "via the JWT_SECRET environment variable."
        )
    await init_db()
    await _seed_admin()
    yield

app = FastAPI(title="Golf Tracker", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
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
app.include_router(users_router.router, dependencies=_auth)

@app.get("/health")
async def health():
    return {"status": "ok"}
