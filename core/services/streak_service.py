from datetime import date, timedelta
from typing import Tuple, List
from core.models.user import UserProfile
from core.interfaces.repository import IProgressRepository

class StreakService:
    def __init__(self, repository: IProgressRepository):
        self.repository = repository

    async def update_user_streak(self, user_id: int) -> Tuple[int, int]:
        """
        Updates streak based on solving a problem today.
        Returns: (current_streak, longest_streak)
        """
        user = await self.repository.get_or_create_user(user_id)
        today = date.today()
        today_str = today.isoformat()

        current_streak = user.current_streak
        longest_streak = user.longest_streak

        if user.last_active_date:
            last_date = date.fromisoformat(user.last_active_date)
            diff = (today - last_date).days
            if diff == 0:
                # Already solved something today
                return current_streak, longest_streak
            elif diff == 1:
                # Continuous streak
                current_streak += 1
            else:
                # Streak broken
                current_streak = 1
        else:
            current_streak = 1

        if current_streak > longest_streak:
            longest_streak = current_streak

        user.current_streak = current_streak
        user.longest_streak = longest_streak
        user.last_active_date = today_str

        await self.repository.save_user(user)
        return current_streak, longest_streak
