import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship

from backend.core.db import Base
from backend.core.types import GUID, JSONField


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    call_id = Column(GUID(), ForeignKey("real_calls.id", ondelete="CASCADE"), nullable=False, unique=True)
    raw_text = Column(Text, nullable=True)
    segments = Column(JSONField, default=list)
    speakers = Column(JSONField, default=list)
    language = Column(String(10), default="en")
    confidence = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("RealCall", back_populates="transcript")

    def __repr__(self):
        return f"<Transcript call={self.call_id}>"
