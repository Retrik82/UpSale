import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship

from backend.core.db import Base
from backend.core.types import GUID, JSONField


class SimulationStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationSession(Base):
    __tablename__ = "simulation_sessions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    client_template_id = Column(GUID(), ForeignKey("client_templates.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    scenario = Column(Text, nullable=True)
    status = Column(String(50), default=SimulationStatus.DRAFT.value, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    user_input = Column(JSONField, default=list)
    ai_responses = Column(JSONField, default=list)
    metrics = Column(JSONField, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    workspace = relationship("Workspace", back_populates="simulations")
    client_template = relationship("ClientTemplate")

    def __repr__(self):
        return f"<SimulationSession {self.name} status={self.status}>"
