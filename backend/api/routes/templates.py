from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.core.security import get_current_user
from backend.models.user import User
from backend.repositories.template_repo import TemplateRepository
from backend.repositories.workspace_repo import WorkspaceRepository

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    pain_points: Optional[List[str]] = None
    objections: Optional[List[str]] = None
    talking_points: Optional[List[str]] = None
    preferred_tone: str = "professional"


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    pain_points: Optional[List[str]] = None
    objections: Optional[List[str]] = None
    talking_points: Optional[List[str]] = None
    preferred_tone: Optional[str] = None


class TemplateResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str]
    company_name: Optional[str]
    industry: Optional[str]
    pain_points: List[str]
    objections: List[str]
    talking_points: List[str]
    preferred_tone: str
    created_at: str

    class Config:
        from_attributes = True


def check_workspace_access(db: Session, workspace_id: UUID, user_id: UUID):
    workspace_repo = WorkspaceRepository(db)
    member = workspace_repo.get_member(workspace_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    return member


@router.get("")
async def list_templates(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_workspace_access(db, workspace_id, current_user.id)
    
    template_repo = TemplateRepository(db)
    templates = template_repo.get_workspace_templates(workspace_id)
    
    return [
        TemplateResponse(
            id=t.id,
            workspace_id=t.workspace_id,
            name=t.name,
            description=t.description,
            company_name=t.company_name,
            industry=t.industry,
            pain_points=t.pain_points or [],
            objections=t.objections or [],
            talking_points=t.talking_points or [],
            preferred_tone=t.preferred_tone,
            created_at=t.created_at.isoformat(),
        )
        for t in templates
    ]


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_workspace_access(db, request.workspace_id, current_user.id)
    
    template_repo = TemplateRepository(db)
    template = template_repo.create(
        workspace_id=request.workspace_id,
        name=request.name,
        description=request.description,
        company_name=request.company_name,
        industry=request.industry,
        pain_points=request.pain_points,
        objections=request.objections,
        talking_points=request.talking_points,
        preferred_tone=request.preferred_tone,
    )
    
    return TemplateResponse(
        id=template.id,
        workspace_id=template.workspace_id,
        name=template.name,
        description=template.description,
        company_name=template.company_name,
        industry=template.industry,
        pain_points=template.pain_points or [],
        objections=template.objections or [],
        talking_points=template.talking_points or [],
        preferred_tone=template.preferred_tone,
        created_at=template.created_at.isoformat(),
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template_repo = TemplateRepository(db)
    template = template_repo.get_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    check_workspace_access(db, template.workspace_id, current_user.id)
    
    return TemplateResponse(
        id=template.id,
        workspace_id=template.workspace_id,
        name=template.name,
        description=template.description,
        company_name=template.company_name,
        industry=template.industry,
        pain_points=template.pain_points or [],
        objections=template.objections or [],
        talking_points=template.talking_points or [],
        preferred_tone=template.preferred_tone,
        created_at=template.created_at.isoformat(),
    )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    request: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template_repo = TemplateRepository(db)
    template = template_repo.get_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    check_workspace_access(db, template.workspace_id, current_user.id)
    
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.company_name is not None:
        template.company_name = request.company_name
    if request.industry is not None:
        template.industry = request.industry
    if request.pain_points is not None:
        template.pain_points = request.pain_points
    if request.objections is not None:
        template.objections = request.objections
    if request.talking_points is not None:
        template.talking_points = request.talking_points
    if request.preferred_tone is not None:
        template.preferred_tone = request.preferred_tone
    
    template = template_repo.update(template)
    
    return TemplateResponse(
        id=template.id,
        workspace_id=template.workspace_id,
        name=template.name,
        description=template.description,
        company_name=template.company_name,
        industry=template.industry,
        pain_points=template.pain_points or [],
        objections=template.objections or [],
        talking_points=template.talking_points or [],
        preferred_tone=template.preferred_tone,
        created_at=template.created_at.isoformat(),
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template_repo = TemplateRepository(db)
    template = template_repo.get_by_id(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    check_workspace_access(db, template.workspace_id, current_user.id)
    
    template_repo.delete(template_id)
