import json
from typing import Dict, List, Optional
from dataclasses import dataclass

from backend.core.config import settings


@dataclass
class AnalysisPrompt:
    system: str
    user: str
    
    @classmethod
    def from_template(cls, template: str, **kwargs) -> "AnalysisPrompt":
        return cls(
            system=cls._get_system_prompt(),
            user=template.format(**kwargs),
        )
    
    @staticmethod
    def _get_system_prompt() -> str:
        return """You are an expert sales coach analyzing a sales call transcript.
Analyze the conversation and provide detailed feedback on:
1. Strengths in the sales approach
2. Areas for improvement
3. Key moments (best and worst)
4. Suggested improvements
5. Objection handling quality

Be specific and actionable in your feedback. Return your analysis as JSON."""


class LLMAnalyzer:
    def __init__(
        self,
        provider: str = "ollama",
        model: str = None,
        base_url: str = None,
    ):
        self.provider = provider
        self.model = model or settings.OLLAMA_MODEL
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.api_key = settings.OPENAI_API_KEY if provider == "openai" else None
    
    async def analyze_transcript(
        self,
        transcript_text: str,
        formatted_transcript: str,
        client_name: Optional[str] = None,
        client_info: Optional[Dict] = None,
    ) -> Dict:
        user_prompt = self._build_analysis_prompt(
            formatted_transcript,
            client_name,
            client_info,
        )
        
        if self.provider == "ollama":
            return await self._analyze_with_ollama(user_prompt)
        elif self.provider == "openai":
            return await self._analyze_with_openai(user_prompt)
        else:
            return self._default_analysis()
    
    async def _analyze_with_ollama(self, prompt: str) -> Dict:
        import httpx
        
        system_prompt = AnalysisPrompt._get_system_prompt()
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": "json",
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("message", {}).get("content", "{}")
                return json.loads(content)
            except Exception as e:
                print(f"Ollama request failed: {e}")
                return self._default_analysis()
    
    async def _analyze_with_openai(self, prompt: str) -> Dict:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=self.api_key)
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": AnalysisPrompt._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"OpenAI request failed: {e}")
            return self._default_analysis()
    
    def _build_analysis_prompt(
        self,
        formatted_transcript: str,
        client_name: Optional[str],
        client_info: Optional[Dict],
    ) -> str:
        client_context = ""
        if client_name:
            client_context = f"\nClient: {client_name}"
        if client_info:
            client_context += f"\nIndustry: {client_info.get('industry', 'N/A')}"
            client_context += f"\nPain Points: {', '.join(client_info.get('pain_points', []))}"
        
        return f"""Analyze this sales call transcript:

{formatted_transcript}
{client_context}

Return a JSON object with the following structure:
{{
    "summary": "Brief 2-3 sentence summary of the call",
    "strengths": ["strength 1", "strength 2", ...],
    "areas_for_improvement": ["area 1", "area 2", ...],
    "key_moments": [
        {{"timestamp": "0:30", "type": "positive", "description": "..."}},
        {{"timestamp": "2:15", "type": "negative", "description": "..."}}
    ],
    "suggested_improvements": "Detailed suggestions for improvement...",
    "handled_objections": ["objection 1", "objection 2"],
    "features_mentioned": ["feature 1", "feature 2"],
    "empathy_phrases": ["phrase 1", "phrase 2"],
    "closing_techniques_used": ["technique 1", "technique 2"]
}}"""
    
    def _default_analysis(self) -> Dict:
        return {
            "summary": "Analysis completed with default metrics.",
            "strengths": ["Unable to complete detailed analysis"],
            "areas_for_improvement": ["Unable to complete detailed analysis"],
            "key_moments": [],
            "suggested_improvements": "Please ensure LLM service is running.",
            "handled_objections": [],
            "features_mentioned": [],
            "empathy_phrases": [],
            "closing_techniques_used": [],
        }
