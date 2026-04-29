from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Round(Base):
    __tablename__ = "rounds"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    course_source = Column(String)
    club_id = Column(Integer, ForeignKey("local_clubs.id"), nullable=True)
    club_name = Column(String)
    course_id = Column(Integer, ForeignKey("local_courses.id"), nullable=True)
    tee_id = Column(Integer, ForeignKey("local_tees.id"), nullable=True)
    course_name = Column(String)
    tee_name = Column(String)
    slope = Column(Float)
    course_rating = Column(Float)
    par_total = Column(Integer)
    hcp_index = Column(Float)
    playing_handicap = Column(Integer)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    scores = relationship("HoleScore", back_populates="round", cascade="all, delete-orphan", order_by="HoleScore.hole_number")

class HoleScore(Base):
    __tablename__ = "hole_scores"
    id = Column(Integer, primary_key=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), nullable=False)
    hole_number = Column(Integer, nullable=False)
    strokes = Column(Integer, nullable=False)
    hole_par = Column(Integer)
    hole_stroke_index = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    round = relationship("Round", back_populates="scores")
