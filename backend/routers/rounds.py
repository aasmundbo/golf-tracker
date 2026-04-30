from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.round import Round, HoleScore
from models.course import LocalClub, LocalCourse, LocalTee, LocalHole
from services.handicap import calculate_playing_handicap, calculate_live_stats, calculate_projected_handicap
from schemas.round import RoundCreate, RoundResponse

router = APIRouter(prefix="/api/rounds", tags=["rounds"])

@router.post("")
async def start_round(data: RoundCreate, db: AsyncSession = Depends(get_db)):
    playing_hcp = calculate_playing_handicap(
        data.hcp_index, data.slope, data.course_rating, data.par_total or 72
    )
    round_data = data.model_dump()

    if data.course_source == 'on_the_fly' and not data.tee_id:
        # Resolve club name: prefer explicit club_name, fall back to course_name
        club_label = data.club_name or data.course_name
        layout_label = data.course_name if data.club_name else 'Bane 1'
        tee_label = data.tee_name or 'Default'

        # Reuse existing club with same name (case-insensitive) if possible
        club_result = await db.execute(
            select(LocalClub).where(LocalClub.name.ilike(club_label))
        )
        club = club_result.scalar_one_or_none()
        if not club:
            club = LocalClub(name=club_label)
            db.add(club)
            await db.flush()

        # Reuse existing layout with same name for this club so hole data persists across rounds
        layout_result = await db.execute(
            select(LocalCourse).where(
                LocalCourse.club_id == club.id,
                LocalCourse.name == layout_label,
            )
        )
        layout = layout_result.scalar_one_or_none()
        if not layout:
            layout = LocalCourse(club_id=club.id, name=layout_label)
            db.add(layout)
            await db.flush()

        # Reuse existing tee with same name so hole data (par/SI) entered on round 1 pre-loads on round 2
        tee_result = await db.execute(
            select(LocalTee).where(
                LocalTee.course_id == layout.id,
                LocalTee.name == tee_label,
            )
        )
        tee = tee_result.scalar_one_or_none()
        if not tee:
            tee = LocalTee(
                course_id=layout.id,
                name=tee_label,
                slope=data.slope,
                course_rating=data.course_rating,
                par_total=data.par_total,
            )
            db.add(tee)
            await db.flush()

        round_data['club_id'] = club.id
        round_data['club_name'] = club.name
        round_data['course_id'] = layout.id
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

# ── Literal-path routes (must come before /{round_id}) ───────────────────────

@router.get("/recent-courses")
async def get_recent_courses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Round).order_by(Round.started_at.desc()))
    rounds = result.scalars().all()
    seen: set[str] = set()
    recent = []
    for r in rounds:
        key = r.course_name or ''
        if key in seen:
            continue
        seen.add(key)
        recent.append({
            "club_name": r.club_name,
            "course_name": r.course_name,
            "tee_name": r.tee_name,
            "tee_id": r.tee_id,
            "slope": r.slope,
            "course_rating": r.course_rating,
            "par_total": r.par_total,
        })
        if len(recent) == 3:
            break
    return recent

@router.get("/{round_id}")
async def get_round(round_id: int, db: AsyncSession = Depends(get_db)):
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
    response = {c.key: getattr(round_, c.key) for c in Round.__table__.columns}
    response["scores"] = scores
    return response

@router.delete("/{round_id}")
async def delete_round(round_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    await db.delete(round_)
    await db.commit()
    return {"ok": True}

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


@router.get("/{round_id}/projected_handicap")
async def get_projected_handicap(round_id: int, db: AsyncSession = Depends(get_db)):
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

    hole_data = []
    if round_.tee_id:
        hole_result = await db.execute(
            select(LocalHole).where(LocalHole.tee_id == round_.tee_id).order_by(LocalHole.hole_number)
        )
        hole_data = [
            {"hole_number": h.hole_number, "par": h.par, "stroke_index": h.stroke_index}
            for h in hole_result.scalars().all()
        ]

    return calculate_projected_handicap(
        scores=scores,
        hole_data=hole_data,
        playing_handicap=round_.playing_handicap,
        course_rating=round_.course_rating,
        slope=round_.slope,
    )
