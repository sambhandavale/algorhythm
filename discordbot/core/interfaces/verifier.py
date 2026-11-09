from abc import ABC, abstractmethod
from typing import Tuple, Optional
from core.models.problem import Problem

class ISubmissionVerifier(ABC):
    @abstractmethod
    async def verify(self, username: str, problem: Problem) -> Tuple[bool, Optional[str]]:
        """
        Verifies whether an Accepted submission exists for the given problem.
        Returns: (is_verified, message_or_submission_id)
        """
        pass
