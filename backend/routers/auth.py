from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import google.oauth2.id_token
import google.auth.transport.requests
from auth import create_access_token
from config import settings
from database import get_db
from models.user import User, UserRole
from limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_google_request = google.auth.transport.requests.Request()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleLoginRequest(BaseModel):
    id_token: str


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.email == data.username))
    user = result.scalar_one_or_none()
    if user is None or user.password_hash is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not _pwd_ctx.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    return TokenResponse(access_token=create_access_token(user_id=user.id))


@router.post("/google", response_model=TokenResponse)
async def google_login(data: GoogleLoginRequest, session: AsyncSession = Depends(get_db)):
    try:
        payload = google.oauth2.id_token.verify_oauth2_token(
            data.id_token, _google_request, settings.google_client_id
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_sub: str = payload["sub"]
    email: str = payload["email"]
    name: str = payload.get("name", email)

    # Match on google_sub first, fall back to email
    result = await session.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()

    if user is None:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(email=email, name=name, google_sub=google_sub, role=UserRole.user)
        session.add(user)
    else:
        if user.google_sub is None:
            user.google_sub = google_sub

    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)
    return TokenResponse(access_token=create_access_token(user_id=user.id))
