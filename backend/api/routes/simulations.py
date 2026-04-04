from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.core.security import get_current_user
from backend.models.user import User
from backend.models.simulation_session import SimulationStatus
from backend.repositories.simulation_repo import SimulationRepository
from backend.repositories.workspace_repo import WorkspaceRepository

router = APIRouter(prefix="/simulations", tags=["simulations"])


class SimulationCreate(BaseModel):
    workspace_id: UUID
    name: str
    client_template_id: Optional[UUID] = None
    scenario: Optional[str] = None


class SimulationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    client_template_id: Optional[UUID]
    name: str
    scenario: Optional[str]
    status: str
    duration_seconds: Optional[int]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class SimulationDetailResponse(SimulationResponse):
    transcript: Optional[str] = None
    user_input: list = []
    ai_responses: list = []
    metrics: dict = {}


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
async def list_simulations(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_workspace_access(db, workspace_id, current_user.id)
    
    sim_repo = SimulationRepository(db)
    simulations = sim_repo.get_workspace_simulations(workspace_id)
    
    return [
        SimulationResponse(
            id=s.id,
            workspace_id=s.workspace_id,
            client_template_id=s.client_template_id,
            name=s.name,
            scenario=s.scenario,
            status=s.status,
            duration_seconds=s.duration_seconds,
            created_at=s.created_at.isoformat(),
            started_at=s.started_at.isoformat() if s.started_at else None,
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
        )
        for s in simulations
    ]


@router.post("", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    request: SimulationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_workspace_access(db, request.workspace_id, current_user.id)
    
    sim_repo = SimulationRepository(db)
    simulation = sim_repo.create(
        workspace_id=request.workspace_id,
        name=request.name,
        client_template_id=request.client_template_id,
        scenario=request.scenario,
    )
    
    return SimulationResponse(
        id=simulation.id,
        workspace_id=simulation.workspace_id,
        client_template_id=simulation.client_template_id,
        name=simulation.name,
        scenario=simulation.scenario,
        status=simulation.status,
        duration_seconds=simulation.duration_seconds,
        created_at=simulation.created_at.isoformat(),
        started_at=None,
        completed_at=None,
    )


@router.get("/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation(
    simulation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sim_repo = SimulationRepository(db)
    simulation = sim_repo.get_by_id(simulation_id)
    
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )
    
    check_workspace_access(db, simulation.workspace_id, current_user.id)
    
    return SimulationDetailResponse(
        id=simulation.id,
        workspace_id=simulation.workspace_id,
        client_template_id=simulation.client_template_id,
        name=simulation.name,
        scenario=simulation.scenario,
        status=simulation.status,
        duration_seconds=simulation.duration_seconds,
        created_at=simulation.created_at.isoformat(),
        started_at=simulation.started_at.isoformat() if simulation.started_at else None,
        completed_at=simulation.completed_at.isoformat() if simulation.completed_at else None,
        transcript=simulation.transcript,
        user_input=simulation.user_input or [],
        ai_responses=simulation.ai_responses or [],
        metrics=simulation.metrics or {},
    )


@router.post("/{simulation_id}/start", response_model=SimulationResponse)
async def start_simulation(
    simulation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    
    sim_repo = SimulationRepository(db)
    simulation = sim_repo.get_by_id(simulation_id)
    
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )
    
    check_workspace_access(db, simulation.workspace_id, current_user.id)
    
    simulation.status = SimulationStatus.IN_PROGRESS.value
    simulation.started_at = datetime.utcnow()
    sim_repo.update(simulation)
    
    return SimulationResponse(
        id=simulation.id,
        workspace_id=simulation.workspace_id,
        client_template_id=simulation.client_template_id,
        name=simulation.name,
        scenario=simulation.scenario,
        status=simulation.status,
        duration_seconds=simulation.duration_seconds,
        created_at=simulation.created_at.isoformat(),
        started_at=simulation.started_at.isoformat() if simulation.started_at else None,
        completed_at=None,
    )


@router.post("/{simulation_id}/finish", response_model=SimulationResponse)
async def finish_simulation(
    simulation_id: UUID,
    transcript: str,
    metrics: dict,
    duration_seconds: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sim_repo = SimulationRepository(db)
    simulation = sim_repo.get_by_id(simulation_id)
    
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )
    
    check_workspace_access(db, simulation.workspace_id, current_user.id)
    
    simulation = sim_repo.complete(
        simulation_id=simulation_id,
        transcript=transcript,
        metrics=metrics,
        duration_seconds=duration_seconds,
    )
    
    return SimulationResponse(
        id=simulation.id,
        workspace_id=simulation.workspace_id,
        client_template_id=simulation.client_template_id,
        name=simulation.name,
        scenario=simulation.scenario,
        status=simulation.status,
        duration_seconds=simulation.duration_seconds,
        created_at=simulation.created_at.isoformat(),
        started_at=simulation.started_at.isoformat() if simulation.started_at else None,
        completed_at=simulation.completed_at.isoformat() if simulation.completed_at else None,
    )


class MessageRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []
    client_context: dict = {}


@router.post("/{simulation_id}/message")
async def send_message(
    simulation_id: UUID,
    request: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.ai.client_simulator import ClientSimulator

    sim_repo = SimulationRepository(db)
    simulation = sim_repo.get_by_id(simulation_id)
    
    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )
    
    check_workspace_access(db, simulation.workspace_id, current_user.id)
    
    if simulation.status != SimulationStatus.IN_PROGRESS.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation is not in progress",
        )
    
    try:
        simulator = ClientSimulator()
        response = await simulator.generate_response(
            conversation_history=request.conversation_history,
            client_context=request.client_context,
        )
    except Exception as e:
        print(f"Simulation error: {e}")
        response = "I'm sorry, I'm having trouble responding right now."
    
    return {"response": response}
