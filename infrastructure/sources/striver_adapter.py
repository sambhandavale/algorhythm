import json
from typing import List, Optional, Dict
from core.models.problem import Problem
from core.interfaces.problem_source import IProblemSource
from config import SHEET_PATH

class StriverSheetAdapter(IProblemSource):
    def __init__(self, sheet_path=SHEET_PATH):
        self.sheet_path = sheet_path
        self._problems: List[Problem] = []
        self._problems_by_id: Dict[str, Problem] = {}
        self.load()

    def load(self):
        with open(self.sheet_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        problems_data = raw.get("problems", [])
        self._problems = []
        self._problems_by_id = {}

        for p in problems_data:
            problem = Problem(
                id=p.get("id"),
                order=p.get("order", 0),
                title=p.get("title", ""),
                step=p.get("step", 0),
                step_title=p.get("stepTitle", ""),
                topic=p.get("topic", ""),
                pattern=p.get("topic", ""),  # In Striver A2Z, 'topic' is the specific pattern
                difficulty=p.get("difficulty") or "Medium",
                platform=p.get("platform", "practice"),
                url=p.get("url", ""),
                lc_slug=p.get("lcSlug") or None,
                article=p.get("article") or None,
                video=p.get("video") or None,
                duration=p.get("duration") or None
            )
            self._problems.append(problem)
            self._problems_by_id[problem.id] = problem

    def get_all_problems(self) -> List[Problem]:
        return self._problems

    def get_problem_by_id(self, problem_id: str) -> Optional[Problem]:
        return self._problems_by_id.get(problem_id)

    async def fetch_extra_by_pattern(self, pattern_name: str, topic: str, limit: int = 3) -> List[Problem]:
        # Striver adapter is primary; extra queries are handled by secondary sources
        return []
