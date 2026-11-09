from dataclasses import dataclass
from typing import Optional

@dataclass
class UserProfile:
    user_id: int
    leetcode_username: Optional[str] = None
    channel_id: int = 0  # Daily problem channel
    notes_channel_id: int = 0  # Pattern notes channel
    reminder_hour: int = 8
    reminder_minute: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    last_active_date: Optional[str] = None
    active_pattern: Optional[str] = None
    pattern_started_date: Optional[str] = None

@dataclass
class ProgressRecord:
    user_id: int
    problem_id: str
    slug: str
    status: str  # 'SOLVED' or 'SKIPPED'
    solved_at: str
    source: str  # 'LEETCODE' or 'MANUAL'
