import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from backend.core.db import Base
from backend.core.types import GUID, JSONField


class ClientTemplate(Base):
    __tablename__ = "client_templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(GUID(), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    company_name = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    pain_points = Column(JSONField, default=list)
    objections = Column(JSONField, default=list)
    talking_points = Column(JSONField, default=list)
    preferred_tone = Column(String(50), default="professional")
    meta_data = Column("metadata", JSONField, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="templates")

    def __repr__(self):
        return f"<ClientTemplate {self.name}>"
