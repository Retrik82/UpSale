from typing import Dict, List, Optional
from dataclasses import asdict

from backend.analysis.parser import TranscriptParser, ParsedTranscript
from backend.analysis.metrics import MetricsCalculator, SalesMetrics
from backend.analysis.llm import LLMAnalyzer


class ReportGenerator:
    def __init__(
        self,
        seller_label: str = "Seller",
        client_label: str = "Client",
    ):
        self.parser = TranscriptParser()
        self.metrics_calculator = MetricsCalculator(seller_label, client_label)
        self.llm_analyzer = LLMAnalyzer()
    
    async def generate_report(
        self,
        transcript_result: Dict,
        client_name: Optional[str] = None,
        client_info: Optional[Dict] = None,
    ) -> Dict:
        transcript = self.parser.parse(transcript_result)
        formatted = self.parser.format_for_llm(transcript)
        
        llm_analysis = await self.llm_analyzer.analyze_transcript(
            transcript_result.get("text", ""),
            formatted,
            client_name,
            client_info,
        )
        
        metrics = self.metrics_calculator.calculate(transcript, llm_analysis)
        
        report = {
            "overall_score": metrics.overall_score,
            "talk_ratio_seller": metrics.talk_ratio_seller,
            "talk_ratio_client": metrics.talk_ratio_client,
            "engagement_score": metrics.engagement_score,
            "objection_handling_score": metrics.objection_handling_score,
            "closing_score": metrics.closing_score,
            "product_knowledge_score": metrics.product_knowledge_score,
            "communication_clarity_score": metrics.communication_clarity_score,
            "strengths": llm_analysis.get("strengths", []),
            "areas_for_improvement": llm_analysis.get("areas_for_improvement", []),
            "key_moments": llm_analysis.get("key_moments", []),
            "suggested_improvements": llm_analysis.get("suggested_improvements", ""),
            "summary": llm_analysis.get("summary", ""),
            "full_analysis": self._format_full_analysis(llm_analysis, metrics),
            "metadata": {
                "client_name": client_name,
                "client_info": client_info,
                "llm_analysis": llm_analysis,
            },
        }
        
        return report
    
    def _format_full_analysis(self, llm_analysis: Dict, metrics: SalesMetrics) -> str:
        lines = [
            "=== SALES CALL ANALYSIS REPORT ===",
            "",
            f"Overall Score: {metrics.overall_score}/100",
            "",
            "--- Performance Scores ---",
            f"Engagement: {metrics.engagement_score}/100",
            f"Objection Handling: {metrics.objection_handling_score}/100",
            f"Closing: {metrics.closing_score}/100",
            f"Product Knowledge: {metrics.product_knowledge_score}/100",
            f"Communication Clarity: {metrics.communication_clarity_score}/100",
            "",
            f"Talk Ratio - Seller: {metrics.talk_ratio_seller*100:.1f}%",
            f"Talk Ratio - Client: {metrics.talk_ratio_client*100:.1f}%",
            "",
            "--- Summary ---",
            llm_analysis.get("summary", ""),
            "",
            "--- Strengths ---",
            *llm_analysis.get("strengths", []),
            "",
            "--- Areas for Improvement ---",
            *llm_analysis.get("areas_for_improvement", []),
            "",
            "--- Suggested Improvements ---",
            llm_analysis.get("suggested_improvements", ""),
        ]
        
        return "\n".join(str(line) for line in lines if line)
