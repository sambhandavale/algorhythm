from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class PatternNote:
    pattern_name: str
    topic: str
    core_intuition: str
    template_code: str
    key_questions: List[str] = field(default_factory=list)
    common_pitfalls: List[str] = field(default_factory=list)

@dataclass
class PatternProgress:
    pattern_name: str
    topic: str
    total_problems: int
    solved_problems: int
    is_completed: bool
    started_at: Optional[str] = None
    days_on_pattern: int = 1
