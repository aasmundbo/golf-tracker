from pydantic import BaseModel, Field
from typing import Optional

class RoundCreate(BaseModel):
    course_source: str = "on_the_fly"
    club_id: Optional[int] = None
    club_name: Optional[str] = None
    course_id: Optional[int] = None
    tee_id: Optional[int] = None
    course_name: str
    tee_name: Optional[str] = None
    slope: float
    course_rating: float
    par_total: Optional[int] = 72
    city: Optional[str] = None
    country: Optional[str] = None
    hcp_index: float = Field(..., ge=0.0, le=54.0)

class RoundResponse(BaseModel):
    id: int
    club_name: Optional[str]
    course_name: str
    playing_handicap: int
    status: str
    class Config:
        from_attributes = True
