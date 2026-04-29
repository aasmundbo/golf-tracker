from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.course import LocalCourse, LocalTee, LocalHole
from services import course_resolver, course_api
from schemas.course import (
    CourseCreate, CourseUpdate, TeeCreate, TeeUpdate, HoleUpsert,
    CourseResponse, TeeResponse
)

router = APIRouter(prefix="/api/courses", tags=["courses"])

@router.get("/search")
async def search_courses(q: str, db: AsyncSession = Depends(get_db)):
    return await course_resolver.search(q, db)

@router.get("/local")
async def list_local_courses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse))
    courses = result.scalars().all()
    return courses

@router.post("/local")
async def create_local_course(data: CourseCreate, db: AsyncSession = Depends(get_db)):
    course = LocalCourse(**data.model_dump())
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course

@router.get("/local/{course_id}")
async def get_local_course(course_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse).where(LocalCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")
    return course

@router.put("/local/{course_id}")
async def update_local_course(course_id: int, data: CourseUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse).where(LocalCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    await db.commit()
    return course

@router.delete("/local/{course_id}")
async def delete_local_course(course_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse).where(LocalCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")
    await db.delete(course)
    await db.commit()
    return {"ok": True}

@router.post("/local/{course_id}/tees")
async def add_tee(course_id: int, data: TeeCreate, db: AsyncSession = Depends(get_db)):
    tee = LocalTee(course_id=course_id, **data.model_dump())
    db.add(tee)
    await db.commit()
    await db.refresh(tee)
    return tee

@router.put("/local/{course_id}/tees/{tee_id}")
async def update_tee(course_id: int, tee_id: int, data: TeeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalTee).where(LocalTee.id == tee_id, LocalTee.course_id == course_id))
    tee = result.scalar_one_or_none()
    if not tee:
        raise HTTPException(404, "Tee not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(tee, k, v)
    await db.commit()
    return tee

@router.post("/local/{course_id}/tees/{tee_id}/holes")
async def upsert_hole(course_id: int, tee_id: int, data: HoleUpsert, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LocalHole).where(LocalHole.tee_id == tee_id, LocalHole.hole_number == data.hole_number)
    )
    hole = result.scalar_one_or_none()
    if hole:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(hole, k, v)
    else:
        hole = LocalHole(tee_id=tee_id, **data.model_dump())
        db.add(hole)
    await db.commit()
    await db.refresh(hole)
    return hole

@router.get("/local/tees/{tee_id}/holes")
async def get_tee_holes(tee_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LocalHole).where(LocalHole.tee_id == tee_id).order_by(LocalHole.hole_number)
    )
    return result.scalars().all()

@router.get("/{course_id}")
async def get_course(course_id: str, db: AsyncSession = Depends(get_db)):
    if course_id.startswith("local:"):
        lid = int(course_id.split(":")[1])
        result = await db.execute(select(LocalCourse).where(LocalCourse.id == lid))
        course = result.scalar_one_or_none()
        if not course:
            raise HTTPException(404)
        return {"source": "local", "course": course}
    elif course_id.startswith("api:"):
        aid = course_id.split(":")[1]
        data = await course_api.get_course(aid, db)
        if not data:
            raise HTTPException(404)
        return {"source": "api", "course": data}
    raise HTTPException(400, "Invalid course id format")
