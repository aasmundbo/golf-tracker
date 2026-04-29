from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.round import Round, HoleScore
from models.course import LocalCourse, LocalTee
from services.handicap import calculate_playing_handicap, calculate_live_stats
from schemas.round import RoundCreate, RoundResponse

router = APIRouter(prefix="/api/rounds", tags=["rounds"])

@router.post("")
async def start_round(data: RoundCreate, db: AsyncSession = Depends(get_db)):
    playing_hcp = calculate_playing_handicap(
        data.hcp_index, data.slope, data.course_rating, data.par_total or 72
    )
    round_data = data.model_dump()

    # Auto-create a local course+tee for on-the-fly rounds so hole data has somewhere to live
    if data.course_source == 'on_the_fly' and not data.tee_id:
        course = LocalCourse(name=data.course_name)
        db.add(course)
        await db.flush()
        tee = LocalTee(
            course_id=course.id,
            name=data.tee_name or 'Default',
            slope=data.slope,
            course_rating=data.course_rating,
            par_total=data.par_total,
        )
        db.add(tee)
        await db.flush()
        round_data['course_id'] = course.id
        round_data['tee_id'] = tee.id
        round_data['course_source'] = 'local'

    round_ = Round(
        **round_data,
        playing_handicap=playing_hcp,
        status="active",
    )
    db.add(round_)
    await db.commit()
    await db.refresh(round_)
    return round_

@router.get("")
async def list_rounds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Round).order_by(Round.started_at.desc()))
    return result.scalars().all()

@router.get("/{round_id}")
async def get_round(round_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    return round_

@router.put("/{round_id}/finish")
async def finish_round(round_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    from datetime import datetime
    round_.status = "finished"
    round_.finished_at = datetime.utcnow()
    await db.commit()
    return round_

@router.get("/{round_id}/live")
async def get_live_stats(round_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    score_result = await db.execute(
        select(HoleScore).where(HoleScore.round_id == round_id).order_by(HoleScore.hole_number)
    )
    scores = [
        {
            "hole_number": s.hole_number,
            "strokes": s.strokes,
            "hole_par": s.hole_par,
            "hole_stroke_index": s.hole_stroke_index,
        }
        for s in score_result.scalars().all()
    ]
    stats = calculate_live_stats(scores, round_.playing_handicap)
    return {**stats, "playing_handicap": round_.playing_handicap, "hcp_index": round_.hcp_index}
