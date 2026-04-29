from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.round import HoleScore, Round
from schemas.score import ScoreCreate, ScoreUpdate

router = APIRouter(prefix="/api/rounds", tags=["scores"])

@router.post("/{round_id}/scores")
async def record_score(round_id: int, data: ScoreCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Round).where(Round.id == round_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Round not found")
    score = HoleScore(round_id=round_id, **data.model_dump())
    db.add(score)
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
    await db.commit()
    return score
