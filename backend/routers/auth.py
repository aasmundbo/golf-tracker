from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth import create_access_token
from database import get_db
from models.user import User
from limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.email == data.username))
    user = result.scalar_one_or_none()
    if user is None or user.password_hash is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not _pwd_ctx.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user_id=user.id))
