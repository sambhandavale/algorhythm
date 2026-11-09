import os
from typing import Optional, List
from core.models.problem import Problem
from core.interfaces.ai_tutor import IAITutor
from infrastructure.ai.gemini_adapter import GeminiAdapter
from infrastructure.ai.grok_adapter import GrokAdapter

class MultiProviderAITutor(IAITutor):
    """
    Composite AI Tutor that supports both Grok (xAI) and Google Gemini.
    Prioritizes user's chosen provider, and automatically falls back if one fails.
    """
    def __init__(self):
        self.grok = GrokAdapter()
        self.gemini = GeminiAdapter()

        # Determine primary provider
        preferred = os.getenv("AI_PROVIDER", "").lower()
        if preferred == "grok" or (not preferred and self.grok.api_key):
            self.primary = self.grok
            self.secondary = self.gemini if self.gemini.api_key else None
        else:
            self.primary = self.gemini
            self.secondary = self.grok if self.grok.api_key else None

    async def get_socratic_hint(self, problem: Problem, user_query: str, hint_level: int = 1) -> str:
        res = await self.primary.get_socratic_hint(problem, user_query, hint_level)
        if "error" in res.lower() and self.secondary:
            return await self.secondary.get_socratic_hint(problem, user_query, hint_level)
        return res

    async def review_code(self, problem: Problem, code: str) -> str:
        res = await self.primary.review_code(problem, code)
        if "error" in res.lower() and self.secondary:
            return await self.secondary.review_code(problem, code)
        return res

    async def ask_concept(self, topic_or_pattern: str, question: str) -> str:
        res = await self.primary.ask_concept(topic_or_pattern, question)
        if "error" in res.lower() and self.secondary:
            return await self.secondary.ask_concept(topic_or_pattern, question)
        return res

    async def generate_pattern_insight(self, pattern_name: str, topic: str, problem_title: str) -> str:
        res = await self.primary.generate_pattern_insight(pattern_name, topic, problem_title)
        if "error" in res.lower() and self.secondary:
            return await self.secondary.generate_pattern_insight(pattern_name, topic, problem_title)
        return res

    async def generate_drill_problems(self, pattern_name: str, topic: str, count: int = 3) -> List[dict]:
        res = await self.primary.generate_drill_problems(pattern_name, topic, count)
        if not res and self.secondary:
            return await self.secondary.generate_drill_problems(pattern_name, topic, count)
        return res

def get_ai_tutor() -> IAITutor:
    return MultiProviderAITutor()
