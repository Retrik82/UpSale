from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from backend.core.db import get_db
from backend.core.security import get_current_user
from backend.models.user import User
from backend.models.workspace_member import WorkspaceRole
from backend.repositories.workspace_repo import WorkspaceRepository

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    owner_id: UUID
    created_at: str

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    full_name: Optional[str]
    role: str
    created_at: str


class AddMemberRequest(BaseModel):
    email: str
    role: WorkspaceRole = WorkspaceRole.MEMBER


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace_repo = WorkspaceRepository(db)
    workspaces = workspace_repo.get_user_workspaces(current_user.id)
    return [
        WorkspaceResponse(
            id=w.id,
            name=w.name,
            description=w.description,
            owner_id=w.owner_id,
            created_at=w.created_at.isoformat(),
        )
        for w in workspaces
    ]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace_repo = WorkspaceRepository(db)
    workspace = workspace_repo.create(
        name=request.name,
        owner_id=current_user.id,
        description=request.description,
    )
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at.isoformat(),
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace_repo = WorkspaceRepository(db)
    member = workspace_repo.get_member(workspace_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    workspace = workspace_repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at.isoformat(),
    )


@router.get("/{workspace_id}/members", response_model=list[MemberResponse])
async def list_workspace_members(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace_repo = WorkspaceRepository(db)
    member = workspace_repo.get_member(workspace_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    members = workspace_repo.get_workspace_members(workspace_id)
    return [
        MemberResponse(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email,
            full_name=m.user.full_name,
            role=m.role.value,
            created_at=m.created_at.isoformat(),
        )
        for m in members
    ]


@router.post("/{workspace_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: UUID,
    request: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.repositories.user_repo import UserRepository
    
    workspace_repo = WorkspaceRepository(db)
    user_repo = UserRepository(db)
    
    current_member = workspace_repo.get_member(workspace_id, current_user.id)
    if not current_member or current_member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add members",
        )
    
    user_to_add = user_repo.get_by_email(request.email)
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    existing = workspace_repo.get_member(workspace_id, user_to_add.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member",
        )
    
    member = workspace_repo.add_member(
        workspace_id=workspace_id,
        user_id=user_to_add.id,
        role=request.role,
    )
    
    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=user_to_add.email,
        full_name=user_to_add.full_name,
        role=member.role.value,
        created_at=member.created_at.isoformat(),
    )
