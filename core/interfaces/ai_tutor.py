from abc import ABC, abstractmethod
from typing import Optional
from core.models.problem import Problem

class IAITutor(ABC):
    @abstractmethod
    async def get_socratic_hint(self, problem: Problem, user_query: str, hint_level: int = 1) -> str:
        """Generates a progressive Socratic hint without spoiling the solution."""
        pass

    @abstractmethod
    async def review_code(self, problem: Problem, code: str) -> str:
        """Reviews code for Time/Space complexity, edge cases, and optimizations."""
        pass

    @abstractmethod
    async def ask_concept(self, topic_or_pattern: str, question: str) -> str:
        """Explains a DSA concept or algorithm in an intuitive manner."""
        pass

    @abstractmethod
    async def generate_pattern_insight(self, pattern_name: str, topic: str, problem_title: str) -> str:
        """Generates a fresh, bite-sized tip, mental model, or interview trap for the pattern."""
        pass
