from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from database import get_db
from models.course import LocalClub, LocalCourse, LocalTee, LocalHole
from services import course_resolver, course_api
from schemas.course import (
    ClubCreate, ClubUpdate, LayoutCreate, LayoutUpdate,
    CourseCreate, CourseUpdate, TeeCreate, TeeUpdate, HoleUpsert,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])

# ── Search (literal path — must come before parameterized routes) ─────────────

@router.get("/search")
async def search_courses(q: str, db: AsyncSession = Depends(get_db)):
    return await course_resolver.search(q, db)

# ── Top-level course CRUD (LocalClub → "Bane" to user) ───────────────────────

@router.get("")
async def list_courses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalClub))
    return result.scalars().all()

@router.post("")
async def create_course(data: ClubCreate, db: AsyncSession = Depends(get_db)):
    club = LocalClub(**data.model_dump())
    db.add(club)
    await db.commit()
    await db.refresh(club)
    return club

@router.get("/{course_id:int}/layouts")
async def list_layouts(course_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse).where(LocalCourse.club_id == course_id))
    return result.scalars().all()

@router.post("/{course_id:int}/layouts")
async def create_layout(course_id: int, data: LayoutCreate, db: AsyncSession = Depends(get_db)):
    layout = LocalCourse(club_id=course_id, **data.model_dump())
    db.add(layout)
    await db.commit()
    await db.refresh(layout)
    return layout

@router.get("/{course_id:int}")
async def get_course_by_id(course_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalClub).where(LocalClub.id == course_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(404, "Course not found")
    return club

@router.put("/{course_id:int}")
async def update_course(course_id: int, data: ClubUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalClub).where(LocalClub.id == course_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(404, "Course not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(club, k, v)
    await db.commit()
    return club

@router.delete("/{course_id:int}")
async def delete_course(course_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalClub).where(LocalClub.id == course_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(404, "Course not found")
    await db.delete(club)
    await db.commit()
    return {"ok": True}

# ── Local layout CRUD (/local/* — literal prefix, no conflict with /{int}) ────

@router.get("/local")
async def list_local_layouts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse))
    return result.scalars().all()

@router.post("/local")
async def create_local_layout(data: CourseCreate, db: AsyncSession = Depends(get_db)):
    layout = LocalCourse(**data.model_dump())
    db.add(layout)
    await db.commit()
    await db.refresh(layout)
    return layout

@router.get("/local/tees/{tee_id}/holes")
async def get_tee_holes(tee_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LocalHole).where(LocalHole.tee_id == tee_id).order_by(LocalHole.hole_number)
    )
    return result.scalars().all()

@router.get("/local/{layout_id:int}/tees")
async def list_layout_tees(layout_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalTee).where(LocalTee.course_id == layout_id))
    return result.scalars().all()

@router.get("/local/{layout_id:int}")
async def get_local_layout(layout_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse).where(LocalCourse.id == layout_id))
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(404, "Layout not found")
    return layout

@router.put("/local/{layout_id:int}")
async def update_local_layout(layout_id: int, data: LayoutUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse).where(LocalCourse.id == layout_id))
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(404, "Layout not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(layout, k, v)
    await db.commit()
    return layout

@router.delete("/local/{layout_id:int}")
async def delete_local_layout(layout_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse).where(LocalCourse.id == layout_id))
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(404, "Layout not found")
    await db.delete(layout)
    await db.commit()
    return {"ok": True}

@router.post("/local/{layout_id:int}/tees")
async def add_tee(layout_id: int, data: TeeCreate, db: AsyncSession = Depends(get_db)):
    tee = LocalTee(course_id=layout_id, **data.model_dump())
    db.add(tee)
    await db.commit()
    await db.refresh(tee)
    return tee

@router.put("/local/{layout_id:int}/tees/{tee_id}")
async def update_tee(layout_id: int, tee_id: int, data: TeeUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LocalTee).where(LocalTee.id == tee_id, LocalTee.course_id == layout_id)
    )
    tee = result.scalar_one_or_none()
    if not tee:
        raise HTTPException(404, "Tee not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(tee, k, v)
    await db.commit()
    return tee

@router.post("/local/{layout_id:int}/tees/{tee_id}/holes")
async def upsert_hole(layout_id: int, tee_id: int, data: HoleUpsert, db: AsyncSession = Depends(get_db)):
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

# ── Catch-all for prefixed IDs like "local:5" or "api:3" (MUST BE LAST) ──────

@router.get("/{prefixed_id}")
async def get_course_by_prefixed_id(prefixed_id: str, db: AsyncSession = Depends(get_db)):
    if prefixed_id.startswith("local:"):
        lid = int(prefixed_id.split(":")[1])
        result = await db.execute(
            select(LocalCourse)
            .options(selectinload(LocalCourse.tees).selectinload(LocalTee.holes))
            .where(LocalCourse.id == lid)
        )
        layout = result.scalar_one_or_none()
        if not layout:
            raise HTTPException(404)
        return {"source": "local", "course": layout}
    elif prefixed_id.startswith("api:"):
        aid = prefixed_id.split(":")[1]
        data = await course_api.get_course(aid, db)
        if not data:
            raise HTTPException(404)
        return {"source": "api", "course": data}
    raise HTTPException(400, "Invalid course id format")
