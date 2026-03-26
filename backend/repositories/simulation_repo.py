import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.models.simulation_session import SimulationSession, SimulationStatus


class SimulationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, simulation_id: uuid.UUID) -> Optional[SimulationSession]:
        return self.db.query(SimulationSession).filter(SimulationSession.id == simulation_id).first()

    def get_workspace_simulations(self, workspace_id: uuid.UUID) -> List[SimulationSession]:
        return (
            self.db.query(SimulationSession)
            .filter(SimulationSession.workspace_id == workspace_id)
            .order_by(SimulationSession.created_at.desc())
            .all()
        )

    def create(
        self,
        workspace_id: uuid.UUID,
        name: str,
        client_template_id: Optional[uuid.UUID] = None,
        scenario: Optional[str] = None,
    ) -> SimulationSession:
        simulation = SimulationSession(
            workspace_id=workspace_id,
            client_template_id=client_template_id,
            name=name,
            scenario=scenario,
            status=SimulationStatus.DRAFT.value,
        )
        self.db.add(simulation)
        self.db.commit()
        self.db.refresh(simulation)
        return simulation

    def update(self, simulation: SimulationSession) -> SimulationSession:
        self.db.commit()
        self.db.refresh(simulation)
        return simulation

    def update_status(self, simulation_id: uuid.UUID, status: SimulationStatus) -> Optional[SimulationSession]:
        simulation = self.get_by_id(simulation_id)
        if simulation:
            simulation.status = status.value
            self.db.commit()
            self.db.refresh(simulation)
        return simulation

    def add_interaction(
        self,
        simulation_id: uuid.UUID,
        user_input: str,
        ai_response: str,
    ) -> Optional[SimulationSession]:
        simulation = self.get_by_id(simulation_id)
        if simulation:
            user_input_list = simulation.user_input or []
            ai_responses_list = simulation.ai_responses or []
            user_input_list.append(user_input)
            ai_responses_list.append(ai_response)
            simulation.user_input = user_input_list
            simulation.ai_responses = ai_responses_list
            self.db.commit()
            self.db.refresh(simulation)
        return simulation

    def complete(
        self,
        simulation_id: uuid.UUID,
        transcript: str,
        metrics: dict,
        duration_seconds: int,
    ) -> Optional[SimulationSession]:
        from datetime import datetime
        simulation = self.get_by_id(simulation_id)
        if simulation:
            simulation.status = SimulationStatus.COMPLETED.value
            simulation.transcript = transcript
            simulation.metrics = metrics
            simulation.duration_seconds = duration_seconds
            simulation.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(simulation)
        return simulation

    def delete(self, simulation_id: uuid.UUID) -> bool:
        simulation = self.get_by_id(simulation_id)
        if simulation:
            self.db.delete(simulation)
            self.db.commit()
            return True
        return False
