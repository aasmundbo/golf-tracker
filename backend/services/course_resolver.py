from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from models.course import LocalCourse, LocalClub
from services import course_api

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

    try:
        api_results = await course_api.search_courses(query, db)
        api_formatted = [
            {
                "source": "api",
                "id": f"api:{c['id']}",
                "name": c.get("course_name", ""),
                "club_name": c.get("club_name", ""),
                "city": c.get("location", {}).get("city", ""),
                "country": c.get("location", {}).get("country", ""),
            }
            for c in api_results
        ]
    except Exception:
        api_formatted = []

    return local_results + api_formatted
