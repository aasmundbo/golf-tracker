from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from models.course import LocalCourse, LocalClub

async def search(query: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(LocalCourse)
        .options(selectinload(LocalCourse.club))
        .outerjoin(LocalClub, LocalCourse.club_id == LocalClub.id)
        .where(
            or_(
                LocalCourse.name.ilike(f"%{query}%"),
                LocalClub.name.ilike(f"%{query}%"),
            )
        )
    )
    local = result.scalars().all()
    matched_club_ids = {c.club_id for c in local if c.club_id is not None}
    local_results = [
        {
            "source": "local",
            "id": f"local:{c.id}",
            "name": c.name,
            "club_name": c.club.name if c.club else None,
            "city": c.club.city if c.club else None,
            "country": c.club.country if c.club else None,
        }
        for c in local
    ]

    # Also include clubs that matched but have no layouts yet
    club_result = await db.execute(
        select(LocalClub).where(LocalClub.name.ilike(f"%{query}%"))
    )
    for club in club_result.scalars().all():
        if club.id not in matched_club_ids:
            local_results.append({
                "source": "local",
                "id": f"local_club:{club.id}",
                "name": club.name,
                "club_name": club.name,
                "city": club.city,
                "country": club.country,
            })

    return local_results
