import uuid
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from backend.core.security import verify_password, get_password_hash
from backend.models.workspace import Workspace
from backend.models.workspace_member import WorkspaceMember, WorkspaceRole


class WorkspaceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, workspace_id: uuid.UUID) -> Optional[Workspace]:
        return self.db.query(Workspace).filter(Workspace.id == workspace_id).first()

    def get_by_id_with_members(self, workspace_id: uuid.UUID) -> Optional[Workspace]:
        return (
            self.db.query(Workspace)
            .options(joinedload(Workspace.members).joinedload(WorkspaceMember.user))
            .filter(Workspace.id == workspace_id)
            .first()
        )

    def get_user_workspaces(self, user_id: uuid.UUID) -> List[Workspace]:
        return (
            self.db.query(Workspace)
            .join(WorkspaceMember)
            .filter(WorkspaceMember.user_id == user_id)
            .all()
        )

    def create(self, name: str, owner_id: uuid.UUID, description: Optional[str] = None, password: Optional[str] = None) -> Workspace:
        workspace = Workspace(
            name=name,
            description=description,
            owner_id=owner_id,
            password=password,
        )
        self.db.add(workspace)
        self.db.flush()
        
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def update(self, workspace: Workspace) -> Workspace:
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def delete(self, workspace_id: uuid.UUID) -> bool:
        workspace = self.get_by_id(workspace_id)
        if workspace:
            self.db.delete(workspace)
            self.db.commit()
            return True
        return False

    def add_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID, role: WorkspaceRole = WorkspaceRole.MEMBER) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        member = (
            self.db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )
        if member:
            self.db.delete(member)
            self.db.commit()
            return True
        return False

    def get_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Optional[WorkspaceMember]:
        return (
            self.db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )

    def get_workspace_members(self, workspace_id: uuid.UUID) -> List[WorkspaceMember]:
        return (
            self.db.query(WorkspaceMember)
            .options(joinedload(WorkspaceMember.user))
            .filter(WorkspaceMember.workspace_id == workspace_id)
            .all()
        )

    def join_by_password(self, workspace_id: uuid.UUID, user_id: uuid.UUID, password: str) -> Optional[WorkspaceMember]:
        workspace = self.get_by_id(workspace_id)
        if not workspace or not workspace.password:
            return None
        if not verify_password(password, workspace.password):
            return None
        existing = self.get_member(workspace_id, user_id)
        if existing:
            return existing
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=WorkspaceRole.MEMBER,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member
