from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError


JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()


class SystemRole(str, Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class CallStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


stores = {
    "users": {},
    "workspaces": {},
    "workspace_members": {},
    "calls": {},
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


class User:
    def __init__(
        self,
        id: UUID,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        system_role: SystemRole = SystemRole.EMPLOYEE,
        is_blocked: bool = False,
        created_at: datetime = None,
    ):
        self.id = id
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.system_role = system_role
        self.is_blocked = is_blocked
        self.created_at = created_at or datetime.utcnow()


class Workspace:
    def __init__(
        self,
        id: UUID,
        name: str,
        owner_id: UUID,
        description: Optional[str] = None,
        password: Optional[str] = None,
        created_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.description = description
        self.password = password
        self.created_at = created_at or datetime.utcnow()


class WorkspaceMember:
    def __init__(
        self,
        id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole = WorkspaceRole.MEMBER,
        created_at: datetime = None,
    ):
        self.id = id
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.role = role
        self.created_at = created_at or datetime.utcnow()


class RealCall:
    def __init__(
        self,
        id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        client_name: Optional[str] = None,
        notes: Optional[str] = None,
        sale_completed: bool = False,
        status: str = CallStatus.PENDING.value,
        created_at: datetime = None,
    ):
        self.id = id
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.client_name = client_name
        self.notes = notes
        self.sale_completed = sale_completed
        self.status = status
        self.created_at = created_at or datetime.utcnow()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = stores["users"].get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


app = FastAPI(title="Sales Training API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    system_role: str
    is_blocked: bool
    created_at: str


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    password: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    created_at: str


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    role: str
    created_at: str


class JoinByPasswordRequest(BaseModel):
    password: str


class SetWorkspacePasswordRequest(BaseModel):
    password: str


class CallCreate(BaseModel):
    workspace_id: str
    client_name: Optional[str] = None
    notes: Optional[str] = None


class CallResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    client_name: Optional[str]
    notes: Optional[str]
    sale_completed: bool
    status: str
    created_at: str


class UpdateSaleCompletedRequest(BaseModel):
    sale_completed: bool


class SalesStatsResponse(BaseModel):
    total_calls: int
    successful_sales: int
    conversion_rate: float


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    for user in stores["users"].values():
        if user.email == request.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    
    user = User(
        id=uuid4(),
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
    )
    stores["users"][str(user.id)] = user
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        system_role=user.system_role.value,
        is_blocked=user.is_blocked,
        created_at=user.created_at.isoformat(),
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = None
    for u in stores["users"].values():
        if u.email == request.email:
            user = u
            break
    
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token)


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        system_role=current_user.system_role.value,
        is_blocked=current_user.is_blocked,
        created_at=current_user.created_at.isoformat(),
    )


@app.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(current_user: User = Depends(get_current_user)):
    workspace_ids = set()
    for member in stores["workspace_members"].values():
        if member.user_id == str(current_user.id):
            workspace_ids.add(member.workspace_id)
    
    return [
        WorkspaceResponse(
            id=w.id,
            name=w.name,
            description=w.description,
            owner_id=w.owner_id,
            created_at=w.created_at.isoformat(),
        )
        for w in stores["workspaces"].values()
        if w.id in workspace_ids
    ]


@app.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
):
    workspace = Workspace(
        id=uuid4(),
        name=request.name,
        owner_id=str(current_user.id),
        description=request.description,
    )
    stores["workspaces"][workspace.id] = workspace
    
    member = WorkspaceMember(
        id=uuid4(),
        workspace_id=workspace.id,
        user_id=str(current_user.id),
        role=WorkspaceRole.OWNER,
    )
    stores["workspace_members"][member.id] = member
    
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at.isoformat(),
    )


@app.get("/workspaces/{workspace_id}/members", response_model=list[MemberResponse])
async def list_workspace_members(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    member = None
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id and m.user_id == str(current_user.id):
            member = m
            break
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    result = []
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id:
            user = stores["users"].get(m.user_id)
            if user:
                result.append(MemberResponse(
                    id=m.id,
                    user_id=m.user_id,
                    email=user.email,
                    role=m.role.value,
                    created_at=m.created_at.isoformat(),
                ))
    return result


@app.post("/{workspace_id}/join", response_model=MemberResponse)
async def join_workspace_by_password(
    workspace_id: str,
    request: JoinByPasswordRequest,
    current_user: User = Depends(get_current_user),
):
    workspace = stores["workspaces"].get(workspace_id)
    if not workspace or not workspace.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workspace has no password or not found",
        )
    if not verify_password(request.password, workspace.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workspace password",
        )
    
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id and m.user_id == str(current_user.id):
            user = stores["users"].get(m.user_id)
            return MemberResponse(
                id=m.id,
                user_id=m.user_id,
                email=user.email if user else "",
                role=m.role.value,
                created_at=m.created_at.isoformat(),
            )
    
    member = WorkspaceMember(
        id=uuid4(),
        workspace_id=workspace_id,
        user_id=str(current_user.id),
        role=WorkspaceRole.MEMBER,
    )
    stores["workspace_members"][member.id] = member
    
    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=current_user.email,
        role=member.role.value,
        created_at=member.created_at.isoformat(),
    )


@app.post("/workspaces/{workspace_id}/set-password", response_model=WorkspaceResponse)
async def set_workspace_password(
    workspace_id: str,
    request: SetWorkspacePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    workspace = stores["workspaces"].get(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    member = None
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id and m.user_id == str(current_user.id):
            member = m
            break
    
    if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to set workspace password",
        )
    
    workspace.password = get_password_hash(request.password) if request.password else None
    
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at.isoformat(),
    )


@app.delete("/workspaces/{workspace_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: str,
    target_user_id: str,
    current_user: User = Depends(get_current_user),
):
    workspace = stores["workspaces"].get(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    member = None
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id and m.user_id == str(current_user.id):
            member = m
            break
    
    if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove members",
        )
    
    for m_id, m in list(stores["workspace_members"].items()):
        if m.workspace_id == workspace_id and m.user_id == target_user_id:
            del stores["workspace_members"][m_id]


@app.get("/calls", response_model=list[CallResponse])
async def list_calls(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    member = None
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id and m.user_id == str(current_user.id):
            member = m
            break
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    return [
        CallResponse(
            id=c.id,
            workspace_id=c.workspace_id,
            user_id=c.user_id,
            client_name=c.client_name,
            notes=c.notes,
            sale_completed=c.sale_completed,
            status=c.status,
            created_at=c.created_at.isoformat(),
        )
        for c in stores["calls"].values()
        if c.workspace_id == workspace_id
    ]


@app.post("/calls", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    request: CallCreate,
    current_user: User = Depends(get_current_user),
):
    workspace = stores["workspaces"].get(request.workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    member = None
    for m in stores["workspace_members"].values():
        if m.workspace_id == request.workspace_id and m.user_id == str(current_user.id):
            member = m
            break
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    call = RealCall(
        id=uuid4(),
        workspace_id=request.workspace_id,
        user_id=str(current_user.id),
        client_name=request.client_name,
        notes=request.notes,
    )
    stores["calls"][call.id] = call
    
    return CallResponse(
        id=call.id,
        workspace_id=call.workspace_id,
        user_id=call.user_id,
        client_name=call.client_name,
        notes=call.notes,
        sale_completed=call.sale_completed,
        status=call.status,
        created_at=call.created_at.isoformat(),
    )


@app.get("/calls/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
):
    call = stores["calls"].get(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    
    member = None
    for m in stores["workspace_members"].values():
        if m.workspace_id == call.workspace_id and m.user_id == str(current_user.id):
            member = m
            break
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    return CallResponse(
        id=call.id,
        workspace_id=call.workspace_id,
        user_id=call.user_id,
        client_name=call.client_name,
        notes=call.notes,
        sale_completed=call.sale_completed,
        status=call.status,
        created_at=call.created_at.isoformat(),
    )


@app.patch("/calls/{call_id}/sale-completed", response_model=CallResponse)
async def update_sale_completed(
    call_id: str,
    request: UpdateSaleCompletedRequest,
    current_user: User = Depends(get_current_user),
):
    call = stores["calls"].get(call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    
    member = None
    for m in stores["workspace_members"].values():
        if m.workspace_id == call.workspace_id and m.user_id == str(current_user.id):
            member = m
            break
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    call.sale_completed = request.sale_completed
    
    return CallResponse(
        id=call.id,
        workspace_id=call.workspace_id,
        user_id=call.user_id,
        client_name=call.client_name,
        notes=call.notes,
        sale_completed=call.sale_completed,
        status=call.status,
        created_at=call.created_at.isoformat(),
    )


@app.get("/admin/employees", response_model=list[UserResponse])
async def list_employees(current_user: User = Depends(get_current_user)):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view employees",
        )
    
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            system_role=u.system_role.value,
            is_blocked=u.is_blocked,
            created_at=u.created_at.isoformat(),
        )
        for u in stores["users"].values()
        if u.system_role == SystemRole.EMPLOYEE
    ]


@app.post("/admin/employees/{user_id}/block", response_model=UserResponse)
async def block_employee(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can block employees",
        )
    
    user = stores["users"].get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    user.is_blocked = True
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        system_role=user.system_role.value,
        is_blocked=user.is_blocked,
        created_at=user.created_at.isoformat(),
    )


@app.delete("/admin/employees/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete employees",
        )
    
    if user_id not in stores["users"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    del stores["users"][user_id]
    
    for m_id, m in list(stores["workspace_members"].items()):
        if m.user_id == user_id:
            del stores["workspace_members"][m_id]


@app.get("/admin/workspaces/{workspace_id}/stats", response_model=SalesStatsResponse)
async def get_workspace_stats(
    workspace_id: str,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view workspace stats",
        )
    
    workspace = stores["workspaces"].get(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    
    member = None
    for m in stores["workspace_members"].values():
        if m.workspace_id == workspace_id and m.user_id == str(current_user.id):
            member = m
            break
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    
    calls = [
        c for c in stores["calls"].values()
        if c.workspace_id == workspace_id
    ]
    
    if user_id:
        calls = [c for c in calls if c.user_id == user_id]
    
    total_calls = len(calls)
    successful_sales = sum(1 for c in calls if c.sale_completed)
    conversion_rate = (successful_sales / total_calls * 100) if total_calls > 0 else 0.0
    
    return SalesStatsResponse(
        total_calls=total_calls,
        successful_sales=successful_sales,
        conversion_rate=conversion_rate,
    )


@app.post("/admin/workspaces/{workspace_id}/members/{target_user_id}/remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member_from_workspace(
    workspace_id: str,
    target_user_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.system_role != SystemRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can remove members",
        )
    
    for m_id, m in list(stores["workspace_members"].items()):
        if m.workspace_id == workspace_id and m.user_id == target_user_id:
            del stores["workspace_members"][m_id]


@app.get("/health")
async def health_check():
    return {"status": "ok"}