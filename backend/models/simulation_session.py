import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from backend.core.db import Base


class SimulationStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationSession(Base):
    __tablename__ = "simulation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    client_template_id = Column(UUID(as_uuid=True), ForeignKey("client_templates.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    scenario = Column(Text, nullable=True)
    status = Column(String(50), default=SimulationStatus.DRAFT.value, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    user_input = Column(JSONB, default=list)
    ai_responses = Column(JSONB, default=list)
    metrics = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    workspace = relationship("Workspace", back_populates="simulations")
    client_template = relationship("ClientTemplate")

    def __repr__(self):
        return f"<SimulationSession {self.name} status={self.status}>"
