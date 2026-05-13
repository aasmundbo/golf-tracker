from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.round import HoleScore, Round
from models.course import LocalHole
from models.user import User, UserRole
from schemas.score import ScoreCreate, ScoreUpdate
from auth import get_current_user

router = APIRouter(prefix="/api/rounds", tags=["scores"])

async def _upsert_local_hole(db: AsyncSession, tee_id: int, hole_number: int, par: int, stroke_index: int) -> None:
    result = await db.execute(
        select(LocalHole).where(LocalHole.tee_id == tee_id, LocalHole.hole_number == hole_number)
    )
    hole = result.scalar_one_or_none()
    if hole:
        hole.par = par
        hole.stroke_index = stroke_index
    else:
        db.add(LocalHole(tee_id=tee_id, hole_number=hole_number, par=par, stroke_index=stroke_index))

@router.post("/{round_id}/scores")
async def record_score(
    round_id: int,
    data: ScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404, "Round not found")
    if current_user.role != UserRole.admin and round_.user_id != current_user.id:
        raise HTTPException(403, "Forbidden")
    existing = await db.execute(
        select(HoleScore).where(HoleScore.round_id == round_id, HoleScore.hole_number == data.hole_number)
    )
    score = existing.scalar_one_or_none()
    if score:
        for k, v in data.model_dump().items():
            setattr(score, k, v)
    else:
        score = HoleScore(round_id=round_id, **data.model_dump())
        db.add(score)
    if round_.tee_id and data.hole_par and data.hole_stroke_index:
        await _upsert_local_hole(db, round_.tee_id, data.hole_number, data.hole_par, data.hole_stroke_index)
    await db.commit()
    await db.refresh(score)
    return score

@router.put("/{round_id}/scores/{hole_number}")
async def update_score(round_id: int, hole_number: int, data: ScoreUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HoleScore).where(HoleScore.round_id == round_id, HoleScore.hole_number == hole_number)
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(404)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(score, k, v)
    if data.hole_par and data.hole_stroke_index:
        round_result = await db.execute(select(Round).where(Round.id == round_id))
        round_ = round_result.scalar_one_or_none()
        if round_ and round_.tee_id:
            await _upsert_local_hole(db, round_.tee_id, hole_number, data.hole_par, data.hole_stroke_index)
    await db.commit()
    return score
