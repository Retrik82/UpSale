from typing import Dict, List
from dataclasses import dataclass

from backend.analysis.parser import ParsedTranscript, TranscriptParser


@dataclass
class SalesMetrics:
    talk_ratio_seller: float
    talk_ratio_client: float
    engagement_score: int
    objection_handling_score: int
    closing_score: int
    product_knowledge_score: int
    communication_clarity_score: int
    overall_score: int
    
    def to_dict(self) -> Dict:
        return {
            "talk_ratio_seller": self.talk_ratio_seller,
            "talk_ratio_client": self.talk_ratio_client,
            "engagement_score": self.engagement_score,
            "objection_handling_score": self.objection_handling_score,
            "closing_score": self.closing_score,
            "product_knowledge_score": self.product_knowledge_score,
            "communication_clarity_score": self.communication_clarity_score,
            "overall_score": self.overall_score,
        }


class MetricsCalculator:
    def __init__(self, seller_label: str = "Seller", client_label: str = "Client"):
        self.seller_label = seller_label
        self.client_label = client_label
    
    def calculate(self, transcript: ParsedTranscript, analysis: Dict = None) -> SalesMetrics:
        talk_ratios = self._calculate_talk_ratios(transcript)
        
        engagement = self._calculate_engagement(transcript)
        objection_handling = self._calculate_objection_handling(transcript, analysis)
        closing = self._calculate_closing(transcript)
        product_knowledge = self._calculate_product_knowledge(transcript, analysis)
        communication = self._calculate_communication_clarity(transcript)
        
        overall = int(
            engagement * 0.2 +
            objection_handling * 0.25 +
            closing * 0.25 +
            product_knowledge * 0.15 +
            communication * 0.15
        )
        
        return SalesMetrics(
            talk_ratio_seller=talk_ratios["seller"],
            talk_ratio_client=talk_ratios["client"],
            engagement_score=engagement,
            objection_handling_score=objection_handling,
            closing_score=closing,
            product_knowledge_score=product_knowledge,
            communication_clarity_score=communication,
            overall_score=min(100, max(0, overall)),
        )
    
    def _calculate_talk_ratios(self, transcript: ParsedTranscript) -> Dict[str, float]:
        seller_duration = transcript.get_speaker_duration(self.seller_label)
        client_duration = transcript.get_speaker_duration(self.client_label)
        
        if transcript.total_duration == 0:
            return {"seller": 0.5, "client": 0.5}
        
        seller_ratio = seller_duration / transcript.total_duration
        client_ratio = client_duration / transcript.total_duration
        
        return {
            "seller": round(seller_ratio, 2),
            "client": round(client_ratio, 2),
        }
    
    def _calculate_engagement(self, transcript: ParsedTranscript) -> int:
        seller_segments = transcript.get_speaker_segments(self.seller_label)
        questions = TranscriptParser.extract_questions(transcript.raw_text)
        
        score = 50
        score += min(20, len(seller_segments) * 2)
        score += min(15, len(questions) * 5)
        
        avg_seller_words = sum(
            len(seg.get("text", "").split()) for seg in seller_segments
        ) / max(1, len(seller_segments))
        
        if 10 <= avg_seller_words <= 30:
            score += 15
        
        return min(100, max(0, score))
    
    def _calculate_objection_handling(self, transcript: ParsedTranscript, analysis: Dict = None) -> int:
        objections = TranscriptParser.extract_objections(transcript.raw_text)
        
        score = 50
        
        if analysis and "handled_objections" in analysis:
            handled = len(analysis["handled_objections"])
            score += handled * 15
        
        if len(objections) > 0 and analysis:
            if "empathy_phrases" in analysis:
                score += min(20, len(analysis["empathy_phrases"]) * 5)
        
        if not objections:
            score = 70
        
        return min(100, max(0, score))
    
    def _calculate_closing(self, transcript: ParsedTranscript) -> int:
        closing_attempts = TranscriptParser.extract_closing_attempts(transcript.raw_text)
        
        score = 30
        score += min(30, len(closing_attempts) * 15)
        
        if len(closing_attempts) >= 2:
            score += 20
        elif len(closing_attempts) >= 1:
            score += 10
        
        return min(100, max(0, score))
    
    def _calculate_product_knowledge(self, transcript: ParsedTranscript, analysis: Dict = None) -> int:
        score = 50
        
        product_keywords = [
            "product", "service", "feature", "benefit", "solution",
            "price", "quality", "guarantee", "support"
        ]
        
        text_lower = transcript.raw_text.lower()
        keyword_count = sum(1 for kw in product_keywords if kw in text_lower)
        score += min(25, keyword_count * 5)
        
        if analysis and "features_mentioned" in analysis:
            score += min(25, len(analysis["features_mentioned"]) * 8)
        
        return min(100, max(0, score))
    
    def _calculate_communication_clarity(self, transcript: ParsedTranscript) -> int:
        seller_segments = transcript.get_speaker_segments(self.seller_label)
        
        score = 60
        
        avg_words = sum(
            len(seg.get("text", "").split()) for seg in seller_segments
        ) / max(1, len(seller_segments))
        
        if 5 <= avg_words <= 40:
            score += 20
        elif avg_words > 40:
            score += 10
        
        long_pauses = sum(
            1 for i, seg in enumerate(transcript.segments[1:], 1)
            if seg.get("start", 0) - transcript.segments[i-1].get("end", 0) > 5
        )
        score -= min(20, long_pauses * 5)
        
        return min(100, max(0, score))
