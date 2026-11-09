import json
from typing import Optional, List, Dict, Set
from config import SHEET_PATH

class SheetManager:
    def __init__(self, sheet_path=SHEET_PATH):
        self.sheet_path = sheet_path
        self.meta = {}
        self.problems: List[dict] = []
        self.problems_by_id: Dict[str, dict] = {}
        self.problems_by_lc_slug: Dict[str, dict] = {}
        self.load_data()

    def load_data(self):
        with open(self.sheet_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.meta = data.get("meta", {})
            self.problems = data.get("problems", [])

        # Index for fast lookup
        for p in self.problems:
            pid = p.get("id")
            if pid:
                self.problems_by_id[pid] = p
            lc_slug = p.get("lcSlug")
            if lc_slug:
                self.problems_by_lc_slug[lc_slug.lower()] = p

    def get_problem_by_id(self, problem_id: str) -> Optional[dict]:
        return self.problems_by_id.get(problem_id)

    def get_problem_by_lc_slug(self, lc_slug: str) -> Optional[dict]:
        return self.problems_by_lc_slug.get(lc_slug.lower())

    def get_next_problem(self, solved_ids: Set[str], preferred_step: Optional[int] = None) -> Optional[dict]:
        """
        Finds the first unsolved problem in Striver's sheet sequence.
        If preferred_step is provided, only searches within that step.
        """
        for p in self.problems:
            if preferred_step is not None and p.get("step") != preferred_step:
                continue
            if p["id"] not in solved_ids:
                return p
        return None

    def get_progress_summary(self, solved_ids: Set[str]) -> dict:
        total_problems = len(self.problems)
        solved_count = len([p for p in self.problems if p["id"] in solved_ids])
        overall_percentage = (solved_count / total_problems * 100) if total_problems else 0

        # Step breakdown
        steps_map: Dict[str, Dict] = {}
        for p in self.problems:
            step_num = p.get("step", 0)
            step_title = p.get("stepTitle", f"Step {step_num}")
            key = f"Step {step_num}: {step_title}"

            if key not in steps_map:
                steps_map[key] = {"total": 0, "solved": 0}

            steps_map[key]["total"] += 1
            if p["id"] in solved_ids:
                steps_map[key]["solved"] += 1

        return {
            "total": total_problems,
            "solved": solved_count,
            "percentage": overall_percentage,
            "steps": steps_map
        }
