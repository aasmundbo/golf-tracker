from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.course import LocalCourse
from services import course_api

async def search(query: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(LocalCourse).where(LocalCourse.name.ilike(f"%{query}%"))
    )
    local = result.scalars().all()
    local_results = [
        {"source": "local", "id": f"local:{c.id}", "name": c.name, "city": c.city, "country": c.country}
        for c in local
    ]

    try:
        api_results = await course_api.search_courses(query, db)
        api_formatted = [
            {
                "source": "api",
                "id": f"api:{c['id']}",
                "name": c.get("course_name", ""),
                "club": c.get("club_name", ""),
                "city": c.get("location", {}).get("city", ""),
                "country": c.get("location", {}).get("country", ""),
            }
            for c in api_results
        ]
    except Exception:
        api_formatted = []

    return local_results + api_formatted
