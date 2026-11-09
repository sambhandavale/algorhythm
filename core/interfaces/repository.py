from abc import ABC, abstractmethod
from typing import Optional, Set, List, Dict
from core.models.user import UserProfile, ProgressRecord

class IProgressRepository(ABC):
    @abstractmethod
    async def init(self):
        """Initializes storage/tables."""
        pass

    @abstractmethod
    async def get_user(self, user_id: int) -> Optional[UserProfile]:
        pass

    @abstractmethod
    async def get_or_create_user(self, user_id: int) -> UserProfile:
        pass

    @abstractmethod
    async def save_user(self, user: UserProfile):
        pass

    @abstractmethod
    async def get_solved_ids(self, user_id: int) -> Set[str]:
        pass

    @abstractmethod
    async def save_progress(self, record: ProgressRecord):
        pass

    @abstractmethod
    async def get_daily_assignment(self, user_id: int, date_str: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def get_latest_assignment(self, user_id: int) -> Optional[dict]:
        """Returns the most recent assignment regardless of date."""
        pass

    @abstractmethod
    async def set_daily_assignment(self, user_id: int, problem_id: str, date_str: str):
        pass

    @abstractmethod
    async def mark_daily_completed(self, user_id: int, problem_id: str):
        pass

    @abstractmethod
    async def get_all_active_users(self) -> List[UserProfile]:
        pass
