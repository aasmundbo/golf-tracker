from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import Literal, Optional
from auth import get_current_user
from database import get_db
from models.user import User, UserRole
from models.course import LocalClub, LocalCourse
from models.round import Round

router = APIRouter(prefix="/api/users", tags=["users"])


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: UserRole
    preferred_language: str
    score_display: str
    default_hcp_index: Optional[float]
    preferred_tee_gender: Optional[str] = None
    google_sub: Optional[str]

    class Config:
        from_attributes = True


class UserPatch(BaseModel):
    name: Optional[str] = None
    preferred_language: Optional[str] = None
    default_hcp_index: Optional[float] = None
    score_display: Optional[Literal["netto", "brutto"]] = None
    preferred_tee_gender: Optional[str] = None


class UserSearchResult(BaseModel):
    id: int
    display_name: str
    email: str


def _require_admin(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def patch_me(
    data: UserPatch,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if data.name is not None:
        user.name = data.name
    if data.preferred_language is not None:
        user.preferred_language = data.preferred_language
    if data.score_display is not None:
        user.score_display = data.score_display
    if data.default_hcp_index is not None:
        user.default_hcp_index = data.default_hcp_index
    if 'preferred_tee_gender' in data.model_fields_set:
        user.preferred_tee_gender = data.preferred_tee_gender
    await session.commit()
    await session.refresh(user)
    return user


@router.get("")
async def list_users(
    search: Optional[str] = None,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin required")
    if search is not None:
        pattern = f"%{search}%"
        result = await session.execute(
            select(User).where(
                (User.name.ilike(pattern)) | (User.email.ilike(pattern))
            ).limit(20)
        )
        users = result.scalars().all()
        return [UserSearchResult(id=u.id, display_name=u.name, email=u.email) for u in users]
    result = await session.execute(select(User))
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.delete("/me", status_code=204)
async def delete_me(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if current_user.role == UserRole.admin:
        raise HTTPException(status_code=400, detail="Admin accounts cannot be self-deleted")
    await session.execute(
        delete(Round).where(Round.user_id == current_user.id)
    )
    await session.execute(
        update(LocalClub).where(LocalClub.created_by == current_user.id).values(created_by=None)
    )
    await session.execute(
        update(LocalCourse).where(LocalCourse.created_by == current_user.id).values(created_by=None)
    )
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is not None:
        await session.delete(user)
    await session.commit()


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin required")
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(user)
    await session.commit()
