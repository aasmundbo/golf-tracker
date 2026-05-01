from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from config import settings
from auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    stored_hash = settings.admin_password_hash
    if (
        not stored_hash
        or data.username != settings.admin_username
        or not _pwd_ctx.verify(data.password, stored_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token({"sub": data.username}))
