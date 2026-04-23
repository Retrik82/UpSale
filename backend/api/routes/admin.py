from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.core.security import get_current_user
from backend.models.user import User, SystemRole
from backend.models.workspace_member import WorkspaceRole
from backend.repositories.user_repo import UserRepository
from backend.repositories.workspace_repo import WorkspaceRepository
from backend.repositories.call_repo import CallRepository

router = APIRouter(prefix="/admin", tags=["admin"])


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    system_role: str
    is_blocked: bool
    created_at: str

    class Config:
        from_attributes = True


class SalesStatsResponse(BaseModel):
    total_calls: int
    successful_sales: int
    conversion_rate: float


class SetRoleRequest(BaseModel):
    user_id: UUID
    system_role: SystemRole


@router.get("/employees", response_model=list[UserResponse])
async def list_employees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view employees",
        )
    user_repo = UserRepository(db)
    employees = user_repo.get_all_employees()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            system_role=u.system_role.value,
            is_blocked=u.is_blocked,
            created_at=u.created_at.isoformat(),
        )
        for u in employees
    ]


@router.post("/employees/{user_id}/block", response_model=UserResponse)
async def block_employee(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can block employees",
        )
    user_repo = UserRepository(db)
    user = user_repo.block_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        system_role=user.system_role.value,
        is_blocked=user.is_blocked,
        created_at=user.created_at.isoformat(),
    )


@router.post("/employees/{user_id}/unblock", response_model=UserResponse)
async def unblock_employee(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can unblock employees",
        )
    user_repo = UserRepository(db)
    user = user_repo.unblock_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        system_role=user.system_role.value,
        is_blocked=user.is_blocked,
        created_at=user.created_at.isoformat(),
    )


@router.delete("/employees/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete employees",
        )
    user_repo = UserRepository(db)
    success = user_repo.delete(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.get("/workspaces/{workspace_id}/stats", response_model=SalesStatsResponse)
async def get_workspace_stats(
    workspace_id: UUID,
    user_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view workspace stats",
        )
    workspace_repo = WorkspaceRepository(db)
    member = workspace_repo.get_member(workspace_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    call_repo = CallRepository(db)
    stats = call_repo.get_sale_stats(workspace_id, user_id)
    return SalesStatsResponse(**stats)


@router.post("/workspaces/{workspace_id}/members/{target_user_id}/remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member_from_workspace(
    workspace_id: UUID,
    target_user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove members",
        )
    workspace_repo = WorkspaceRepository(db)
    workspace_repo.remove_member(workspace_id, target_user_id)