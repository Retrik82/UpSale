import httpx

from backend.core.config import settings


class ClientSimulator:
    def __init__(self, model: str = None, base_url: str = None):
        self.model = model or settings.OLLAMA_MODEL
        self.base_url = base_url or settings.OLLAMA_BASE_URL

    async def generate_response(
        self,
        conversation_history: list[dict],
        client_context: dict,
    ) -> str:
        system_prompt = self._build_system_prompt(client_context)
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "")
        except Exception as e:
            print(f"ClientSimulator error: {e}")
            return self._fallback_response()

    def _build_system_prompt(self, context: dict) -> str:
        company = context.get("company_name", "a potential client")
        industry = context.get("industry", "")
        pain_points = context.get("pain_points", [])
        description = context.get("description", "")

        prompt = f"""You are {company}"""
        if industry:
            prompt += f", a company in the {industry} industry"
        prompt += ". "

        if description:
            prompt += f"{description} "

        if pain_points:
            prompt += f"Your main pain points are: {', '.join(pain_points)}. "

        prompt += """You are having a sales call. Stay in character as a realistic customer who:
- May have objections and concerns
- Asks clarifying questions
- Shows interest but may be hesitant
- Uses natural conversation language
- Doesn't give away too much information easily

Respond naturally to the salesperson. Keep responses concise (1-3 sentences typically)."""

        return prompt

    def _fallback_response(self) -> str:
        return "I'm sorry, I'm having trouble responding right now. Could you tell me more about your solution?"
