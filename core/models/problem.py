from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Problem:
    id: str
    order: int
    title: str
    step: int
    step_title: str
    topic: str
    pattern: str  # Subtopic / Pattern name (e.g. "On answers", "Logic Building")
    difficulty: str
    platform: str
    url: str
    lc_slug: Optional[str] = None
    article: Optional[str] = None
    video: Optional[str] = None
    duration: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @property
    def full_pattern_name(self) -> str:
        return f"{self.step_title} › {self.pattern}"
