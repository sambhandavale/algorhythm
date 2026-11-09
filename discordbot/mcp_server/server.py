import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from config import SHEET_PATH, DATABASE_PATH
from core.models.user import ProgressRecord
from core.models.pattern import PatternNote
from infrastructure.database.sqlite_repo import SQLiteRepository
from infrastructure.sources.striver_adapter import StriverSheetAdapter
from infrastructure.sources.leetcode_adapter import LeetCodeAdapter
from core.services.study_manager import StudyManager
from core.services.streak_service import StreakService

async def init_services():
    repo = SQLiteRepository(DATABASE_PATH)
    await repo.init()
    primary = StriverSheetAdapter(SHEET_PATH)
    extra = LeetCodeAdapter()
    study_mgr = StudyManager(primary, repo, extra)
    streak_svc = StreakService(repo)

    # Load pattern notes
    try:
        from pathlib import Path
        notes_file = Path(__file__).resolve().parent.parent / "data" / "pattern_notes.json"
        if notes_file.exists():
            with open(notes_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    study_mgr.register_pattern_note(PatternNote(**item))
    except Exception:
        pass

    return repo, study_mgr, streak_svc

class DSAMCPServer:
    """
    Standard MCP tool provider for IDE AI assistants.
    Provides tools to inspect daily problems, retrieve pattern templates, and mark progress.
    """
    def __init__(self):
        self.repo = None
        self.study_mgr = None
        self.streak_svc = None

    async def setup(self):
        self.repo, self.study_mgr, self.streak_svc = await init_services()

    async def tool_get_daily_problem(self, user_id: int = 1) -> Dict[str, Any]:
        """Returns today's assigned DSA problem with topic, difficulty, and practice URL."""
        problem, is_solved, is_repeated = await self.study_mgr.get_daily_problem(user_id)
        topic, pattern, progress = await self.study_mgr.get_active_pattern_info(user_id)
        return {
            "id": problem.id,
            "title": problem.title,
            "topic": topic,
            "pattern": pattern,
            "difficulty": problem.difficulty,
            "url": problem.url,
            "lc_slug": problem.lc_slug,
            "duration": problem.duration,
            "is_solved": is_solved,
            "is_repeated": is_repeated,
            "pattern_progress": f"{progress.solved_problems}/{progress.total_problems} solved in {pattern}"
        }

    async def tool_get_pattern_notes(self, pattern_name: str) -> Dict[str, Any]:
        """Returns the mental model, intuition, code template, and traps for a DSA pattern."""
        note = self.study_mgr.get_pattern_note(pattern_name)
        if not note:
            return {"error": f"No cheat sheet found for pattern '{pattern_name}'"}
        return {
            "pattern": note.pattern_name,
            "topic": note.topic,
            "intuition": note.core_intuition,
            "template_code": note.template_code,
            "key_questions": note.key_questions,
            "pitfalls": note.common_pitfalls
        }

    async def tool_mark_problem_solved(self, user_id: int, problem_id: str) -> Dict[str, Any]:
        """Marks a problem as solved and updates the user's streak in SQLite."""
        p = self.study_mgr.primary_source.get_problem_by_id(problem_id)
        slug = p.lc_slug if p and p.lc_slug else problem_id
        record = ProgressRecord(
            user_id=user_id,
            problem_id=problem_id,
            slug=slug,
            status="SOLVED",
            solved_at=datetime.now().isoformat(),
            source="MANUAL"
        )
        await self.repo.save_progress(record)
        streak, longest = await self.streak_svc.update_user_streak(user_id)
        return {
            "status": "success",
            "problem_id": problem_id,
            "current_streak": streak,
            "longest_streak": longest
        }

    async def tool_get_extra_drills(self, user_id: int = 1, count: int = 3) -> Dict[str, Any]:
        """Fetches extra bonus problems for the current pattern."""
        drills = await self.study_mgr.get_extra_drills(user_id, limit=count)
        return {
            "count": len(drills),
            "problems": [
                {
                    "title": d.title,
                    "difficulty": d.difficulty,
                    "url": d.url,
                    "platform": d.platform
                }
                for d in drills
            ]
        }
