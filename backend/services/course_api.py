import httpx
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.course import CourseApiCache
from config import settings

API_BASE = "https://api.golfcourseapi.com/v1"
CACHE_TTL_HOURS = 24

async def search_courses(query: str, db: AsyncSession) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/search",
            params={"search_query": query},
            headers={"Authorization": f"Key {settings.golf_course_api_key}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("courses", [])

async def get_course(course_id: str, db: AsyncSession) -> dict | None:
    result = await db.execute(select(CourseApiCache).where(CourseApiCache.external_id == course_id))
    cached = result.scalar_one_or_none()
    if cached:
        age = datetime.utcnow() - cached.cached_at
        if age < timedelta(hours=CACHE_TTL_HOURS):
            return json.loads(cached.raw_json)
        await db.delete(cached)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}/courses/{course_id}",
            headers={"Authorization": f"Key {settings.golf_course_api_key}"},
            timeout=10.0,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        course_data = resp.json().get("course", resp.json())

    cache_entry = CourseApiCache(external_id=course_id, raw_json=json.dumps(course_data))
    db.add(cache_entry)
    await db.commit()
    return course_data
