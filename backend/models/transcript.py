import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from backend.core.db import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("real_calls.id", ondelete="CASCADE"), nullable=False, unique=True)
    raw_text = Column(Text, nullable=True)
    segments = Column(JSONB, default=list)
    speakers = Column(ARRAY(String), default=list)
    language = Column(String(10), default="en")
    confidence = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("RealCall", back_populates="transcript")

    def __repr__(self):
        return f"<Transcript call={self.call_id}>"
