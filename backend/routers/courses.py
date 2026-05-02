from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from database import get_db
from models.course import LocalClub, LocalCourse, LocalTee, LocalHole
from models.user import User, UserRole
from services import course_resolver, course_api
from schemas.course import (
    ClubCreate, ClubUpdate, LayoutCreate, LayoutUpdate,
    CourseCreate, CourseUpdate, TeeCreate, TeeUpdate, HoleUpsert, BulkHoleUpsert,
)
from auth import get_current_user

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
async def create_course(
    data: ClubCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    club = LocalClub(**data.model_dump(), created_by=current_user.id)
    db.add(club)
    await db.commit()
    await db.refresh(club)
    return club

@router.get("/{course_id:int}/layouts")
async def list_layouts(course_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse).where(LocalCourse.club_id == course_id))
    return result.scalars().all()

@router.post("/{course_id:int}/layouts")
async def create_layout(
    course_id: int,
    data: LayoutCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    layout = LocalCourse(
        club_id=course_id,
        name=data.name,
        external_api_id=data.external_api_id,
        created_by=current_user.id,
    )
    db.add(layout)
    await db.flush()
    if data.slope is not None or data.course_rating is not None:
        db.add(LocalTee(
            course_id=layout.id,
            name=data.tee_name or 'Gul',
            slope=data.slope,
            course_rating=data.course_rating,
            par_total=data.par_total,
        ))
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
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(LocalClub)
        .options(
            selectinload(LocalClub.courses)
            .selectinload(LocalCourse.tees)
            .selectinload(LocalTee.holes)
        )
        .where(LocalClub.id == course_id)
    )
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(404, "Course not found")
    if current_user.role != UserRole.admin and club.created_by != current_user.id:
        raise HTTPException(403, "Forbidden")
    await db.delete(club)
    await db.commit()
    return {"ok": True}

# ── Local layout CRUD (/local/* — literal prefix, no conflict with /{int}) ────

@router.get("/local")
async def list_local_layouts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LocalCourse))
    return result.scalars().all()

@router.post("/local")
async def create_local_layout(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    layout = LocalCourse(**data.model_dump(), created_by=current_user.id)
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

@router.put("/local/tees/{tee_id}/holes")
async def bulk_upsert_holes(tee_id: int, data: BulkHoleUpsert, db: AsyncSession = Depends(get_db)):
    tee = await db.get(LocalTee, tee_id)
    if not tee:
        raise HTTPException(404, "Tee not found")
    existing = await db.execute(
        select(LocalHole).where(LocalHole.tee_id == tee_id)
    )
    existing_by_number = {h.hole_number: h for h in existing.scalars().all()}
    for hole_data in data.holes:
        if hole_data.hole_number in existing_by_number:
            hole = existing_by_number[hole_data.hole_number]
            for k, v in hole_data.model_dump(exclude_unset=True).items():
                setattr(hole, k, v)
        else:
            db.add(LocalHole(tee_id=tee_id, **hole_data.model_dump()))
    await db.commit()
    result = await db.execute(
        select(LocalHole).where(LocalHole.tee_id == tee_id).order_by(LocalHole.hole_number)
    )
    return result.scalars().all()

@router.put("/local/tees/{tee_id}")
async def update_tee_flat(tee_id: int, data: TeeUpdate, db: AsyncSession = Depends(get_db)):
    tee = await db.get(LocalTee, tee_id)
    if not tee:
        raise HTTPException(404, "Tee not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(tee, k, v)
    await db.commit()
    await db.refresh(tee)
    return tee


@router.delete("/local/tees/{tee_id}")
async def delete_tee(tee_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LocalTee).options(selectinload(LocalTee.holes)).where(LocalTee.id == tee_id)
    )
    tee = result.scalar_one_or_none()
    if not tee:
        raise HTTPException(404, "Tee not found")
    await db.delete(tee)
    await db.commit()
    return {"ok": True}


@router.post("/local/tees/{tee_id}/duplicate")
async def duplicate_tee(tee_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LocalTee).options(selectinload(LocalTee.holes)).where(LocalTee.id == tee_id)
    )
    src = result.scalar_one_or_none()
    if not src:
        raise HTTPException(404, "Tee not found")
    new_tee = LocalTee(
        course_id=src.course_id,
        name=f"{src.name} (kopi)",
        slope=src.slope,
        course_rating=src.course_rating,
        par_total=src.par_total,
    )
    db.add(new_tee)
    await db.flush()
    for h in src.holes:
        db.add(LocalHole(
            tee_id=new_tee.id,
            hole_number=h.hole_number,
            par=h.par,
            stroke_index=h.stroke_index,
            distance_meters=h.distance_meters,
        ))
    await db.commit()
    result2 = await db.execute(
        select(LocalTee).options(selectinload(LocalTee.holes)).where(LocalTee.id == new_tee.id)
    )
    return result2.scalar_one()


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
async def delete_local_layout(
    layout_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(LocalCourse).where(LocalCourse.id == layout_id))
    layout = result.scalar_one_or_none()
    if not layout:
        raise HTTPException(404, "Layout not found")
    if current_user.role != UserRole.admin and layout.created_by != current_user.id:
        raise HTTPException(403, "Forbidden")
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
        try:
            lid = int(prefixed_id.split(":")[1])
        except (ValueError, IndexError):
            raise HTTPException(400, "Invalid course ID format")
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
        parts = prefixed_id.split(":")
        if len(parts) < 2 or not parts[1]:
            raise HTTPException(400, "Invalid course ID format")
        aid = parts[1]
        data = await course_api.get_course(aid, db)
        if not data:
            raise HTTPException(404)
        return {"source": "api", "course": data}
    raise HTTPException(400, "Invalid course id format")
