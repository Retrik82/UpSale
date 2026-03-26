import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.core.db import Base


class CallStatus(str, Enum):
    RECORDING = "recording"
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class RealCall(Base):
    __tablename__ = "real_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    client_template_id = Column(UUID(as_uuid=True), ForeignKey("client_templates.id", ondelete="SET NULL"), nullable=True)
    recording_path = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(50), default=CallStatus.PENDING.value, nullable=False)
    client_name = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    workspace = relationship("Workspace", back_populates="calls")
    client_template = relationship("ClientTemplate")
    transcript = relationship("Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan")
    report = relationship("CallReport", back_populates="call", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RealCall {self.id} status={self.status}>"
