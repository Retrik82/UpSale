import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ParsedTranscript:
    segments: List[Dict]
    speakers: List[str]
    total_duration: float
    
    @property
    def raw_text(self) -> str:
        return " ".join(seg.get("text", "") for seg in self.segments)
    
    def get_speaker_segments(self, speaker: str) -> List[Dict]:
        return [seg for seg in self.segments if seg.get("speaker") == speaker]
    
    def get_speaker_duration(self, speaker: str) -> float:
        segments = self.get_speaker_segments(speaker)
        return sum(seg.get("end", 0) - seg.get("start", 0) for seg in segments)
    
    def get_speaker_word_count(self, speaker: str) -> int:
        segments = self.get_speaker_segments(speaker)
        text = " ".join(seg.get("text", "") for seg in segments)
        return len(text.split())


class TranscriptParser:
    @staticmethod
    def parse(result: Dict) -> ParsedTranscript:
        segments = result.get("segments", [])
        speakers = list(set(seg.get("speaker", "Unknown") for seg in segments))
        
        total_duration = 0
        if segments:
            total_duration = max(seg.get("end", 0) for seg in segments)
        
        return ParsedTranscript(
            segments=segments,
            speakers=speakers,
            total_duration=total_duration,
        )
    
    @staticmethod
    def format_for_llm(transcript: ParsedTranscript) -> str:
        formatted = []
        for seg in transcript.segments:
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "")
            start = seg.get("start", 0)
            formatted.append(f"[{start:.1f}s] {speaker}: {text}")
        return "\n".join(formatted)
    
    @staticmethod
    def extract_questions(text: str) -> List[str]:
        question_pattern = r'[^.!?]*\?'
        return re.findall(question_pattern, text)
    
    @staticmethod
    def extract_objections(text: str) -> List[str]:
        objection_keywords = [
            "can't", "won't", "don't", "not interested", "too expensive",
            "need to think", "budget", "competitor", "later", "busy"
        ]
        sentences = re.split(r'[.!?]', text)
        objections = [
            s.strip() for s in sentences
            if any(kw in s.lower() for kw in objection_keywords)
        ]
        return objections
    
    @staticmethod
    def extract_closing_attempts(text: str) -> List[str]:
        closing_keywords = [
            "deal", "buy", "purchase", "sign", "commit", "start",
            "today", "order", "合同", "购买", "签约"
        ]
        sentences = re.split(r'[.!?]', text)
        attempts = [
            s.strip() for s in sentences
            if any(kw in s.lower() for kw in closing_keywords)
        ]
        return attempts
