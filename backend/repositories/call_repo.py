import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from backend.models.real_call import RealCall, CallStatus
from backend.models.transcript import Transcript
from backend.models.call_report import CallReport


class CallRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, call_id: uuid.UUID) -> Optional[RealCall]:
        return self.db.query(RealCall).filter(RealCall.id == call_id).first()

    def get_by_id_with_details(self, call_id: uuid.UUID) -> Optional[RealCall]:
        return (
            self.db.query(RealCall)
            .options(
                joinedload(RealCall.transcript),
                joinedload(RealCall.report),
                joinedload(RealCall.client_template),
            )
            .filter(RealCall.id == call_id)
            .first()
        )

    def get_workspace_calls(self, workspace_id: uuid.UUID, limit: int = 100, offset: int = 0) -> List[RealCall]:
        return (
            self.db.query(RealCall)
            .options(joinedload(RealCall.report))
            .filter(RealCall.workspace_id == workspace_id)
            .order_by(RealCall.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create(
        self,
        workspace_id: uuid.UUID,
        client_name: Optional[str] = None,
        client_template_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> RealCall:
        call = RealCall(
            workspace_id=workspace_id,
            client_template_id=client_template_id,
            client_name=client_name,
            notes=notes,
            status=CallStatus.PENDING.value,
        )
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        return call

    def update(self, call: RealCall) -> RealCall:
        self.db.commit()
        self.db.refresh(call)
        return call

    def update_status(self, call_id: uuid.UUID, status: CallStatus) -> Optional[RealCall]:
        call = self.get_by_id(call_id)
        if call:
            call.status = status.value
            if status == CallStatus.COMPLETED:
                call.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(call)
        return call

    def update_sale_completed(self, call_id: uuid.UUID, sale_completed: bool) -> Optional[RealCall]:
        call = self.get_by_id(call_id)
        if call:
            call.sale_completed = sale_completed
            self.db.commit()
            self.db.refresh(call)
        return call

    def get_sale_stats(self, workspace_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> dict:
        from sqlalchemy import func
        query = self.db.query(RealCall).filter(RealCall.workspace_id == workspace_id)
        if user_id:
            from backend.models.workspace_member import WorkspaceMember
            member_ids = self.db.query(WorkspaceMember.user_id).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id
            ).subquery()
            query = query.filter(RealCall.id.in_(member_ids))
        
        total_calls = query.count()
        successful_sales = query.filter(RealCall.sale_completed == True).count()
        return {
            "total_calls": total_calls,
            "successful_sales": successful_sales,
            "conversion_rate": (successful_sales / total_calls * 100) if total_calls > 0 else 0
        }

    def update_recording(self, call_id: uuid.UUID, recording_path: str, duration_seconds: int) -> Optional[RealCall]:
        call = self.get_by_id(call_id)
        if call:
            call.recording_path = recording_path
            call.duration_seconds = duration_seconds
            call.status = CallStatus.PENDING.value
            self.db.commit()
            self.db.refresh(call)
        return call

    def delete(self, call_id: uuid.UUID) -> bool:
        call = self.get_by_id(call_id)
        if call:
            self.db.delete(call)
            self.db.commit()
            return True
        return False

    def create_transcript(
        self,
        call_id: uuid.UUID,
        raw_text: str,
        segments: list,
        speakers: List[str],
        language: str = "en",
        confidence: Optional[int] = None,
        duration_seconds: Optional[int] = None,
    ) -> Transcript:
        transcript = Transcript(
            call_id=call_id,
            raw_text=raw_text,
            segments=segments,
            speakers=speakers,
            language=language,
            confidence=confidence,
            duration_seconds=duration_seconds,
        )
        self.db.add(transcript)
        self.db.commit()
        self.db.refresh(transcript)
        return transcript

    def upsert_transcript(
        self,
        call_id: uuid.UUID,
        raw_text: str,
        segments: list,
        speakers: List[str],
        language: str = "en",
        confidence: Optional[int] = None,
        duration_seconds: Optional[int] = None,
    ) -> Transcript:
        transcript = (
            self.db.query(Transcript)
            .filter(Transcript.call_id == call_id)
            .first()
        )

        if transcript is None:
            return self.create_transcript(
                call_id=call_id,
                raw_text=raw_text,
                segments=segments,
                speakers=speakers,
                language=language,
                confidence=confidence,
                duration_seconds=duration_seconds,
            )

        transcript.raw_text = raw_text
        transcript.segments = segments
        transcript.speakers = speakers
        transcript.language = language
        transcript.confidence = confidence
        transcript.duration_seconds = duration_seconds
        self.db.commit()
        self.db.refresh(transcript)
        return transcript

    def create_report(
        self,
        call_id: uuid.UUID,
        overall_score: int,
        talk_ratio_seller: float,
        talk_ratio_client: float,
        engagement_score: int,
        objection_handling_score: int,
        closing_score: int,
        product_knowledge_score: int,
        communication_clarity_score: int,
        strengths: list,
        areas_for_improvement: list,
        key_moments: list,
        suggested_improvements: Optional[str] = None,
        summary: Optional[str] = None,
        full_analysis: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> CallReport:
        report = CallReport(
            call_id=call_id,
            overall_score=overall_score,
            talk_ratio_seller=talk_ratio_seller,
            talk_ratio_client=talk_ratio_client,
            engagement_score=engagement_score,
            objection_handling_score=objection_handling_score,
            closing_score=closing_score,
            product_knowledge_score=product_knowledge_score,
            communication_clarity_score=communication_clarity_score,
            strengths=strengths,
            areas_for_improvement=areas_for_improvement,
            key_moments=key_moments,
            suggested_improvements=suggested_improvements,
            summary=summary,
            full_analysis=full_analysis,
            meta_data=metadata or {},
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def upsert_report(
        self,
        call_id: uuid.UUID,
        overall_score: int,
        talk_ratio_seller: float,
        talk_ratio_client: float,
        engagement_score: int,
        objection_handling_score: int,
        closing_score: int,
        product_knowledge_score: int,
        communication_clarity_score: int,
        strengths: list,
        areas_for_improvement: list,
        key_moments: list,
        suggested_improvements: Optional[str] = None,
        summary: Optional[str] = None,
        full_analysis: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> CallReport:
        report = (
            self.db.query(CallReport)
            .filter(CallReport.call_id == call_id)
            .first()
        )

        if report is None:
            return self.create_report(
                call_id=call_id,
                overall_score=overall_score,
                talk_ratio_seller=talk_ratio_seller,
                talk_ratio_client=talk_ratio_client,
                engagement_score=engagement_score,
                objection_handling_score=objection_handling_score,
                closing_score=closing_score,
                product_knowledge_score=product_knowledge_score,
                communication_clarity_score=communication_clarity_score,
                strengths=strengths,
                areas_for_improvement=areas_for_improvement,
                key_moments=key_moments,
                suggested_improvements=suggested_improvements,
                summary=summary,
                full_analysis=full_analysis,
                metadata=metadata,
            )

        report.overall_score = overall_score
        report.talk_ratio_seller = talk_ratio_seller
        report.talk_ratio_client = talk_ratio_client
        report.engagement_score = engagement_score
        report.objection_handling_score = objection_handling_score
        report.closing_score = closing_score
        report.product_knowledge_score = product_knowledge_score
        report.communication_clarity_score = communication_clarity_score
        report.strengths = strengths
        report.areas_for_improvement = areas_for_improvement
        report.key_moments = key_moments
        report.suggested_improvements = suggested_improvements
        report.summary = summary
        report.full_analysis = full_analysis
        report.meta_data = metadata or {}
        self.db.commit()
        self.db.refresh(report)
        return report
