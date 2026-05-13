from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class LocalClub(Base):
    __tablename__ = "local_clubs"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String)
    country = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    courses = relationship("LocalCourse", back_populates="club", cascade="all, delete-orphan")

class LocalCourse(Base):
    __tablename__ = "local_courses"
    id = Column(Integer, primary_key=True)
    club_id = Column(Integer, ForeignKey("local_clubs.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    club = relationship("LocalClub", back_populates="courses")
    tees = relationship("LocalTee", back_populates="course", cascade="all, delete-orphan")

class LocalTee(Base):
    __tablename__ = "local_tees"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("local_courses.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    color = Column(String)
    slope = Column(Float)
    course_rating = Column(Float)
    par_total = Column(Integer)
    gender = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    course = relationship("LocalCourse", back_populates="tees")
    holes = relationship("LocalHole", back_populates="tee", cascade="all, delete-orphan", order_by="LocalHole.hole_number")

class LocalHole(Base):
    __tablename__ = "local_holes"
    id = Column(Integer, primary_key=True)
    tee_id = Column(Integer, ForeignKey("local_tees.id"), nullable=False)
    hole_number = Column(Integer, nullable=False)
    par = Column(Integer)
    stroke_index = Column(Integer)
    distance_meters = Column(Integer)
    created_at = Column(DateTime, default=_utcnow)
    tee = relationship("LocalTee", back_populates="holes")

