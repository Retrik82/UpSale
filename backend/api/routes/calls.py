from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.audio.manager import recording_manager, RecordingError
from backend.core.db import get_db
from backend.core.config import settings
from backend.core.security import get_current_user
from backend.models.user import User
from backend.models.real_call import CallStatus
from backend.repositories.call_repo import CallRepository
from backend.repositories.workspace_repo import WorkspaceRepository

router = APIRouter(prefix="/calls", tags=["calls"])


class CallCreate(BaseModel):
    workspace_id: UUID
    client_name: Optional[str] = None
    client_template_id: Optional[UUID] = None
    notes: Optional[str] = None


class CallResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    client_template_id: Optional[UUID]
    recording_path: Optional[str]
    duration_seconds: Optional[int]
    status: str
    client_name: Optional[str]
    notes: Optional[str]
    created_at: str
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class CallDetailResponse(CallResponse):
    transcript: Optional[dict] = None
    report: Optional[dict] = None


class StartRecordingRequest(BaseModel):
    device: Optional[int] = None


class TranscriptionRequest(BaseModel):
    language: Optional[str] = None


def get_transcriber():
    from backend.ai.transcriber import Transcriber

    return Transcriber()


def get_report_generator():
    from backend.analysis.report import ReportGenerator

    return ReportGenerator(seller_label="Seller", client_label="Client")


def normalize_transcript_result(transcript_result: dict) -> dict:
    normalized = dict(transcript_result)
    segments = [dict(segment) for segment in transcript_result.get("segments", [])]

    speaker_order: list[str] = []
    for segment in segments:
        speaker = segment.get("speaker") or "Speaker_1"
        if speaker not in speaker_order:
            speaker_order.append(speaker)

    speaker_map: dict[str, str] = {}
    if speaker_order:
        speaker_map[speaker_order[0]] = "Seller"
    if len(speaker_order) > 1:
        speaker_map[speaker_order[1]] = "Client"

    for speaker in speaker_order[2:]:
        speaker_map[speaker] = speaker

    for segment in segments:
        speaker = segment.get("speaker") or "Speaker_1"
        segment["speaker"] = speaker_map.get(speaker, speaker)

    normalized["segments"] = segments
    normalized["speakers"] = [speaker_map.get(speaker, speaker) for speaker in speaker_order]
    normalized["text"] = transcript_result.get("text", "").strip()
    return normalized


def serialize_call(call) -> CallResponse:
    return CallResponse(
        id=call.id,
        workspace_id=call.workspace_id,
        client_template_id=call.client_template_id,
        recording_path=call.recording_path,
        duration_seconds=call.duration_seconds,
        status=call.status,
        client_name=call.client_name,
        notes=call.notes,
        created_at=call.created_at.isoformat(),
        completed_at=call.completed_at.isoformat() if call.completed_at else None,
    )


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
async def list_calls(
    workspace_id: UUID,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_workspace_access(db, workspace_id, current_user.id)
    
    call_repo = CallRepository(db)
    calls = call_repo.get_workspace_calls(workspace_id, limit, offset)
    
    return [serialize_call(c) for c in calls]


@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    request: CallCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_workspace_access(db, request.workspace_id, current_user.id)
    
    call_repo = CallRepository(db)
    call = call_repo.create(
        workspace_id=request.workspace_id,
        client_name=request.client_name,
        client_template_id=request.client_template_id,
        notes=request.notes,
    )
    
    return serialize_call(call)


@router.get("/{call_id}", response_model=CallDetailResponse)
async def get_call(
    call_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call_repo = CallRepository(db)
    call = call_repo.get_by_id_with_details(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    
    check_workspace_access(db, call.workspace_id, current_user.id)
    
    transcript_data = None
    if call.transcript:
        transcript_data = {
            "id": str(call.transcript.id),
            "raw_text": call.transcript.raw_text,
            "segments": call.transcript.segments,
            "speakers": call.transcript.speakers,
            "language": call.transcript.language,
            "confidence": call.transcript.confidence,
            "duration_seconds": call.transcript.duration_seconds,
        }
    
    report_data = None
    if call.report:
        report_data = {
            "id": str(call.report.id),
            "overall_score": call.report.overall_score,
            "talk_ratio_seller": call.report.talk_ratio_seller,
            "talk_ratio_client": call.report.talk_ratio_client,
            "engagement_score": call.report.engagement_score,
            "objection_handling_score": call.report.objection_handling_score,
            "closing_score": call.report.closing_score,
            "product_knowledge_score": call.report.product_knowledge_score,
            "communication_clarity_score": call.report.communication_clarity_score,
            "strengths": call.report.strengths,
            "areas_for_improvement": call.report.areas_for_improvement,
            "key_moments": call.report.key_moments,
            "suggested_improvements": call.report.suggested_improvements,
            "summary": call.report.summary,
            "full_analysis": call.report.full_analysis,
        }
    
    return CallDetailResponse(
        id=call.id,
        workspace_id=call.workspace_id,
        client_template_id=call.client_template_id,
        recording_path=call.recording_path,
        duration_seconds=call.duration_seconds,
        status=call.status,
        client_name=call.client_name,
        notes=call.notes,
        created_at=call.created_at.isoformat(),
        completed_at=call.completed_at.isoformat() if call.completed_at else None,
        transcript=transcript_data,
        report=report_data,
    )


@router.post("/{call_id}/transcribe", response_model=CallResponse)
async def transcribe_call(
    call_id: UUID,
    request: TranscriptionRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call_repo = CallRepository(db)
    call = call_repo.get_by_id(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    
    check_workspace_access(db, call.workspace_id, current_user.id)
    
    if not call.recording_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recording uploaded for this call",
        )
    
    call_repo.update_status(call_id, CallStatus.TRANSCRIBING)

    try:
        transcriber = get_transcriber()
        transcript_result = transcriber.transcribe(
            call.recording_path,
            language=request.language if request else None,
        )
        transcript_result = normalize_transcript_result(transcript_result)
        call_repo.upsert_transcript(
            call_id=call_id,
            raw_text=transcript_result.get("text", ""),
            segments=transcript_result.get("segments", []),
            speakers=transcript_result.get("speakers", []),
            language=transcript_result.get("language", request.language if request else None) or "unknown",
            duration_seconds=call.duration_seconds,
        )
        call = call_repo.update_status(call_id, CallStatus.PENDING)
    except Exception as exc:
        call_repo.update_status(call_id, CallStatus.FAILED)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {exc}",
        ) from exc
    
    return serialize_call(call)


@router.post("/{call_id}/analyze", response_model=CallResponse)
async def analyze_call(
    call_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call_repo = CallRepository(db)
    call = call_repo.get_by_id(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    
    check_workspace_access(db, call.workspace_id, current_user.id)
    
    if not call.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call must be transcribed before analysis",
        )
    
    call_repo.update_status(call_id, CallStatus.ANALYZING)

    try:
        call = call_repo.get_by_id_with_details(call_id)
        report_generator = get_report_generator()
        client_info = None
        if call.client_template:
            client_info = {
                "industry": call.client_template.industry,
                "pain_points": call.client_template.pain_points or [],
                "company_name": call.client_template.company_name,
                "description": call.client_template.description,
            }
        transcript_result = {
            "text": call.transcript.raw_text or "",
            "segments": call.transcript.segments or [],
            "speakers": call.transcript.speakers or [],
            "language": call.transcript.language or "en",
        }
        report = await report_generator.generate_report(
            transcript_result,
            client_name=call.client_name,
            client_info=client_info,
        )
        call_repo.upsert_report(
            call_id=call_id,
            overall_score=report["overall_score"],
            talk_ratio_seller=report["talk_ratio_seller"],
            talk_ratio_client=report["talk_ratio_client"],
            engagement_score=report["engagement_score"],
            objection_handling_score=report["objection_handling_score"],
            closing_score=report["closing_score"],
            product_knowledge_score=report["product_knowledge_score"],
            communication_clarity_score=report["communication_clarity_score"],
            strengths=report["strengths"],
            areas_for_improvement=report["areas_for_improvement"],
            key_moments=report["key_moments"],
            suggested_improvements=report.get("suggested_improvements"),
            summary=report.get("summary"),
            full_analysis=report.get("full_analysis"),
            metadata=report.get("metadata"),
        )
        call = call_repo.update_status(call_id, CallStatus.COMPLETED)
    except Exception as exc:
        call_repo.update_status(call_id, CallStatus.FAILED)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        ) from exc
    
    return serialize_call(call)


@router.post("/{call_id}/recording/start", response_model=CallResponse)
async def start_recording(
    call_id: UUID,
    request: StartRecordingRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call_repo = CallRepository(db)
    call = call_repo.get_by_id(call_id)

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    check_workspace_access(db, call.workspace_id, current_user.id)

    if recording_manager.is_recording(call_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recording is already running for this call",
        )

    try:
        recording_manager.start(call_id, device=request.device if request else None)
    except RecordingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    call = call_repo.update_status(call_id, CallStatus.RECORDING)
    return serialize_call(call)


@router.post("/{call_id}/recording/stop", response_model=CallResponse)
async def stop_recording(
    call_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call_repo = CallRepository(db)
    call = call_repo.get_by_id(call_id)

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    check_workspace_access(db, call.workspace_id, current_user.id)

    try:
        recording_path, duration = recording_manager.stop(call_id)
    except RecordingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    call = call_repo.update_recording(call_id, recording_path, duration)
    return serialize_call(call)


@router.post("/{call_id}/upload", response_model=CallResponse)
async def upload_recording(
    call_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import os
    import uuid as uuid_lib
    
    call_repo = CallRepository(db)
    call = call_repo.get_by_id(call_id)
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )
    
    check_workspace_access(db, call.workspace_id, current_user.id)
    
    os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".wav"
    filename = f"{uuid_lib.uuid4()}{file_ext}"
    file_path = os.path.join(settings.RECORDINGS_DIR, filename)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    try:
        from backend.audio.writer import AudioWriter

        duration = int(AudioWriter.get_duration(file_path))
    except Exception:
        duration = 0
    
    call_repo.update_recording(call_id, file_path, duration)
    call = call_repo.get_by_id(call_id)

    return serialize_call(call)
