from pydantic import BaseModel, Field
from typing import Optional

class ScoreCreate(BaseModel):
    hole_number: int = Field(..., ge=1, le=18)
    strokes: int = Field(..., ge=1, le=20)
    hole_par: Optional[int] = None
    hole_stroke_index: Optional[int] = None

class ScoreUpdate(BaseModel):
    strokes: Optional[int] = Field(default=None, ge=1, le=20)
    hole_par: Optional[int] = None
    hole_stroke_index: Optional[int] = None
