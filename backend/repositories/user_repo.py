import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.models.user import User, SystemRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_all_employees(self) -> List[User]:
        return self.db.query(User).filter(User.system_role == SystemRole.EMPLOYEE).all()

    def get_all_admins(self) -> List[User]:
        return self.db.query(User).filter(User.system_role == SystemRole.ADMIN).all()

    def create(self, email: str, hashed_password: str, full_name: Optional[str] = None, system_role: SystemRole = SystemRole.EMPLOYEE) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            system_role=system_role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user

    def block_user(self, user_id: uuid.UUID) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user:
            user.is_blocked = True
            self.db.commit()
            self.db.refresh(user)
        return user

    def unblock_user(self, user_id: uuid.UUID) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user:
            user.is_blocked = False
            self.db.commit()
            self.db.refresh(user)
        return user

    def delete(self, user_id: uuid.UUID) -> bool:
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False
