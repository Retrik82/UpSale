import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.models.client_template import ClientTemplate


class TemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, template_id: uuid.UUID) -> Optional[ClientTemplate]:
        return self.db.query(ClientTemplate).filter(ClientTemplate.id == template_id).first()

    def get_workspace_templates(self, workspace_id: uuid.UUID) -> List[ClientTemplate]:
        return (
            self.db.query(ClientTemplate)
            .filter(ClientTemplate.workspace_id == workspace_id)
            .order_by(ClientTemplate.created_at.desc())
            .all()
        )

    def create(
        self,
        workspace_id: uuid.UUID,
        name: str,
        description: Optional[str] = None,
        company_name: Optional[str] = None,
        industry: Optional[str] = None,
        pain_points: Optional[List[str]] = None,
        objections: Optional[List[str]] = None,
        talking_points: Optional[List[str]] = None,
        preferred_tone: str = "professional",
        metadata: Optional[dict] = None,
    ) -> ClientTemplate:
        template = ClientTemplate(
            workspace_id=workspace_id,
            name=name,
            description=description,
            company_name=company_name,
            industry=industry,
            pain_points=pain_points or [],
            objections=objections or [],
            talking_points=talking_points or [],
            preferred_tone=preferred_tone,
            metadata=metadata or {},
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def update(self, template: ClientTemplate) -> ClientTemplate:
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete(self, template_id: uuid.UUID) -> bool:
        template = self.get_by_id(template_id)
        if template:
            self.db.delete(template)
            self.db.commit()
            return True
        return False
