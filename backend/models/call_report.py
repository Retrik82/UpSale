import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Text, ForeignKey, Integer, Float
from sqlalchemy.orm import relationship

from backend.core.db import Base
from backend.core.types import GUID, JSONField


class CallReport(Base):
    __tablename__ = "call_reports"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    call_id = Column(GUID(), ForeignKey("real_calls.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    overall_score = Column(Integer, default=0)
    talk_ratio_seller = Column(Float, default=0.0)
    talk_ratio_client = Column(Float, default=0.0)
    
    engagement_score = Column(Integer, default=0)
    objection_handling_score = Column(Integer, default=0)
    closing_score = Column(Integer, default=0)
    product_knowledge_score = Column(Integer, default=0)
    communication_clarity_score = Column(Integer, default=0)
    
    strengths = Column(JSONField, default=list)
    areas_for_improvement = Column(JSONField, default=list)
    key_moments = Column(JSONField, default=list)
    suggested_improvements = Column(Text, nullable=True)
    
    summary = Column(Text, nullable=True)
    full_analysis = Column(Text, nullable=True)
    meta_data = Column("metadata", JSONField, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("RealCall", back_populates="report")

    def __repr__(self):
        return f"<CallReport call={self.call_id} score={self.overall_score}>"
