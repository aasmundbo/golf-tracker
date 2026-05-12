from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
from database import get_db
from auth import get_current_user
from models.user import User, UserRole
from models.round import Round

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(current_user=Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_require_admin),
):
    # Totals
    total_rounds = (await db.execute(select(func.count(Round.id)))).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    avg_rounds = round(total_rounds / total_users, 1) if total_users else 0

    finished = (await db.execute(
        select(func.count(Round.id)).where(Round.status == "finished")
    )).scalar() or 0
    completion_rate = round(finished / total_rounds * 100) if total_rounds else 0

    # Top 5 courses (club + course + tee)
    top_courses_rows = (await db.execute(
        select(
            Round.club_name,
            Round.course_name,
            Round.tee_name,
            func.count(Round.id).label("count"),
        )
        .group_by(Round.club_name, Round.course_name, Round.tee_name)
        .order_by(func.count(Round.id).desc())
        .limit(5)
    )).all()
    top_courses = [
        {"club_name": r.club_name, "course_name": r.course_name,
         "tee_name": r.tee_name, "count": r.count}
        for r in top_courses_rows
    ]

    # Top 5 users by round count
    top_users_rows = (await db.execute(
        select(
            User.name,
            User.email,
            User.default_hcp_index,
            func.count(Round.id).label("count"),
        )
        .join(Round, Round.user_id == User.id)
        .group_by(User.id, User.name, User.email, User.default_hcp_index)
        .order_by(func.count(Round.id).desc())
        .limit(5)
    )).all()
    top_users = [
        {"name": r.name, "email": r.email,
         "hcp_index": r.default_hcp_index, "count": r.count}
        for r in top_users_rows
    ]

    # Rounds by source type
    source_rows = (await db.execute(
        select(Round.course_source, func.count(Round.id).label("count"))
        .group_by(Round.course_source)
    )).all()
    rounds_by_source = {(r.course_source or "unknown"): r.count for r in source_rows}

    # Inactive users: no round in last 60 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    active_ids = {r[0] for r in (await db.execute(
        select(Round.user_id).where(Round.started_at >= cutoff).distinct()
    )).all()}
    all_ids = {r[0] for r in (await db.execute(select(User.id))).all()}
    inactive_count = len(all_ids - active_ids)

    return {
        "total_rounds": total_rounds,
        "total_users": total_users,
        "avg_rounds_per_user": avg_rounds,
        "completion_rate": completion_rate,
        "top_courses": top_courses,
        "top_users": top_users,
        "rounds_by_source": rounds_by_source,
        "inactive_users": inactive_count,
    }
