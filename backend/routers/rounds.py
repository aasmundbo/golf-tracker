from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone
from database import get_db
from models.round import Round, HoleScore
from models.course import LocalClub, LocalCourse, LocalTee, LocalHole
from models.user import User, UserRole
from services.handicap import calculate_playing_handicap, calculate_live_stats, calculate_projected_handicap
from schemas.round import RoundCreate, RoundResponse
from auth import get_current_user

router = APIRouter(prefix="/api/rounds", tags=["rounds"])


async def _get_deduped_scores(session: AsyncSession, round_id: int) -> list[dict]:
    """Return one score dict per hole (latest entry wins) sorted by hole_number."""
    result = await session.execute(
        select(HoleScore)
        .where(HoleScore.round_id == round_id)
        .order_by(HoleScore.hole_number, HoleScore.id.desc())
    )
    seen: dict[int, dict] = {}
    for s in result.scalars().all():
        if s.hole_number not in seen:
            seen[s.hole_number] = {
                "hole_number": s.hole_number,
                "strokes": s.strokes,
                "hole_par": s.hole_par,
                "hole_stroke_index": s.hole_stroke_index,
            }
    return [seen[h] for h in sorted(seen)]


def _check_ownership(round_: Round, current_user: User) -> None:
    if current_user.role != UserRole.admin and round_.user_id != current_user.id:
        raise HTTPException(403, "Forbidden")


@router.post("")
async def start_round(
    data: RoundCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
            club = LocalClub(name=club_label, city=data.city, country=data.country)
            db.add(club)
            await db.flush()

        # Reuse existing layout with same name for this club so hole data persists across rounds
        layout_result = await db.execute(
            select(LocalCourse).where(
                LocalCourse.club_id == club.id,
                LocalCourse.name.ilike(layout_label),
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
                LocalTee.name.ilike(tee_label),
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
        user_id=current_user.id,
    )
    db.add(round_)
    await db.commit()
    await db.refresh(round_)
    return round_

@router.get("")
async def list_rounds(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin:
        if user_id is not None:
            raise HTTPException(403, "Forbidden")
        result = await db.execute(
            select(Round)
            .where(Round.user_id == current_user.id)
            .order_by(Round.started_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()

    # Admin: join users to include player_name
    stmt = (
        select(Round, User.name.label("player_name"))
        .join(User, Round.user_id == User.id, isouter=True)
        .order_by(Round.started_at.desc())
        .offset(skip).limit(limit)
    )
    if user_id is not None:
        stmt = stmt.where(Round.user_id == user_id)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {**{c.key: getattr(r, c.key) for c in Round.__table__.columns}, "player_name": pname}
        for r, pname in rows
    ]

# ── Literal-path routes (must come before /{round_id}) ───────────────────────

@router.get("/recent-courses")
async def get_recent_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Most recent round per distinct club+course+tee for the current user
    subq = (
        select(func.max(Round.id).label("max_id"))
        .where(Round.user_id == current_user.id)
        .group_by(Round.club_name, Round.course_name, Round.tee_name)
        .subquery()
    )
    result = await db.execute(
        select(Round)
        .where(Round.id.in_(select(subq.c.max_id)))
        .order_by(Round.started_at.desc())
        .limit(2)
    )
    return [
        {
            "club_name": r.club_name,
            "course_name": r.course_name,
            "tee_name": r.tee_name,
            "tee_id": r.tee_id,
            "slope": r.slope,
            "course_rating": r.course_rating,
            "par_total": r.par_total,
        }
        for r in result.scalars().all()
    ]

@router.get("/{round_id}")
async def get_round(
    round_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    _check_ownership(round_, current_user)
    scores = await _get_deduped_scores(db, round_id)
    response = {c.key: getattr(round_, c.key) for c in Round.__table__.columns}
    response["scores"] = scores
    return response

@router.delete("/{round_id}")
async def delete_round(
    round_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    _check_ownership(round_, current_user)
    await db.delete(round_)
    await db.commit()
    return {"ok": True}

@router.put("/{round_id}/finish")
async def finish_round(
    round_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    _check_ownership(round_, current_user)
    round_.status = "finished"
    round_.finished_at = datetime.now(timezone.utc)

    scores = await _get_deduped_scores(db, round_id)
    hole_data = []
    if round_.tee_id:
        hole_result = await db.execute(
            select(LocalHole).where(LocalHole.tee_id == round_.tee_id).order_by(LocalHole.hole_number)
        )
        hole_data = [
            {"hole_number": h.hole_number, "par": h.par, "stroke_index": h.stroke_index}
            for h in hole_result.scalars().all()
        ]
    try:
        proj = calculate_projected_handicap(
            scores=scores,
            hole_data=hole_data,
            playing_handicap=round_.playing_handicap,
            course_rating=round_.course_rating,
            slope=round_.slope,
        )
        round_.projected_hcp = proj["projected_differential"]
    except Exception:
        round_.projected_hcp = None

    await db.commit()
    return round_

@router.get("/{round_id}/live")
async def get_live_stats(
    round_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    _check_ownership(round_, current_user)
    scores = await _get_deduped_scores(db, round_id)
    stats = calculate_live_stats(scores, round_.playing_handicap)
    return {**stats, "playing_handicap": round_.playing_handicap, "hcp_index": round_.hcp_index}


@router.get("/{round_id}/projected_handicap")
async def get_projected_handicap(
    round_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Round).where(Round.id == round_id))
    round_ = result.scalar_one_or_none()
    if not round_:
        raise HTTPException(404)
    _check_ownership(round_, current_user)

    scores = await _get_deduped_scores(db, round_id)

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
