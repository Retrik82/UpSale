import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from backend.core.db import Base


class ClientTemplate(Base):
    __tablename__ = "client_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    company_name = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    pain_points = Column(ARRAY(String), default=list)
    objections = Column(ARRAY(String), default=list)
    talking_points = Column(ARRAY(String), default=list)
    preferred_tone = Column(String(50), default="professional")
    meta_data = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="templates")

    def __repr__(self):
        return f"<ClientTemplate {self.name}>"
