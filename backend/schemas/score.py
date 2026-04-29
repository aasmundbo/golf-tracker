from pydantic import BaseModel
from typing import Optional

class ScoreCreate(BaseModel):
    hole_number: int
    strokes: int
    hole_par: Optional[int] = None
    hole_stroke_index: Optional[int] = None

class ScoreUpdate(BaseModel):
    strokes: Optional[int] = None
    hole_par: Optional[int] = None
    hole_stroke_index: Optional[int] = None
