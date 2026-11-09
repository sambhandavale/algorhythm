from abc import ABC, abstractmethod
from typing import List, Optional
from core.models.problem import Problem

class IProblemSource(ABC):
    @abstractmethod
    def get_all_problems(self) -> List[Problem]:
        """Returns all problems managed by this source."""
        pass

    @abstractmethod
    def get_problem_by_id(self, problem_id: str) -> Optional[Problem]:
        """Looks up a problem by its unique ID."""
        pass

    @abstractmethod
    async def fetch_extra_by_pattern(self, pattern_name: str, topic: str, limit: int = 3) -> List[Problem]:
        """Fetches extra bonus drill problems matching the pattern/topic."""
        pass
