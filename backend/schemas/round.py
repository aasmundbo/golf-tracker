from pydantic import BaseModel
from typing import Optional

class RoundCreate(BaseModel):
    course_source: str = "on_the_fly"
    course_id: Optional[int] = None
    tee_id: Optional[int] = None
    course_name: str
    tee_name: Optional[str] = None
    slope: float
    course_rating: float
    par_total: Optional[int] = 72
    hcp_index: float

class RoundResponse(BaseModel):
    id: int
    course_name: str
    playing_handicap: int
    status: str
    class Config:
        from_attributes = True
