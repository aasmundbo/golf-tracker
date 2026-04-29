from pydantic import BaseModel
from typing import Optional

class CourseCreate(BaseModel):
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    external_api_id: Optional[str] = None

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_verified: Optional[bool] = None

class TeeCreate(BaseModel):
    name: str
    color: Optional[str] = None
    slope: Optional[float] = None
    course_rating: Optional[float] = None
    par_total: Optional[int] = None

class TeeUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    slope: Optional[float] = None
    course_rating: Optional[float] = None
    par_total: Optional[int] = None

class HoleUpsert(BaseModel):
    hole_number: int
    par: Optional[int] = None
    stroke_index: Optional[int] = None
    distance_meters: Optional[int] = None

class CourseResponse(BaseModel):
    id: int
    name: str
    city: Optional[str]
    country: Optional[str]
    is_verified: bool
    class Config:
        from_attributes = True

class TeeResponse(BaseModel):
    id: int
    name: str
    slope: Optional[float]
    course_rating: Optional[float]
    par_total: Optional[int]
    class Config:
        from_attributes = True
