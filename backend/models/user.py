import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship

from backend.core.db import Base
from backend.core.types import GUID, JSONField


class SystemRole(str, Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    settings = Column(JSONField, default=dict)
    system_role = Column(SAEnum(SystemRole), default=SystemRole.EMPLOYEE, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspaces = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
