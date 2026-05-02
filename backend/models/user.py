import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    google_sub = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.user)
    preferred_language = Column(String, nullable=False, default="nb")
    default_hcp_index = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
