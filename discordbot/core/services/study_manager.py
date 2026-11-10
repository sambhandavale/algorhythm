from datetime import date, datetime
from typing import Optional, List, Dict, Set, Tuple
from core.models.problem import Problem
from core.models.pattern import PatternProgress, PatternNote
from core.interfaces.problem_source import IProblemSource
from core.interfaces.repository import IProgressRepository

class StudyManager:
    def __init__(self, primary_source: IProblemSource, repository: IProgressRepository, extra_source: Optional[IProblemSource] = None):
        self.primary_source = primary_source
        self.repository = repository
        self.extra_source = extra_source
        self._pattern_notes: Dict[str, PatternNote] = {}

    def register_pattern_note(self, note: PatternNote):
        self._pattern_notes[note.pattern_name.lower()] = note

    async def get_active_pattern_info(self, user_id: int) -> Tuple[str, str, PatternProgress]:
        """
        Determines the user's current topic, pattern, and progress within that pattern.
        """
        solved_ids = await self.repository.get_solved_ids(user_id)
        all_problems = self.primary_source.get_all_problems()

        # Find the first unsolved problem in chronological sequence
        active_problem = None
        for p in all_problems:
            if p.id not in solved_ids:
                active_problem = p
                break

        if not active_problem:
            # All problems completed!
            last_p = all_problems[-1]
            return last_p.step_title, last_p.pattern, PatternProgress(
                pattern_name=last_p.pattern,
                topic=last_p.step_title,
                total_problems=0,
                solved_problems=0,
                is_completed=True
            )

        active_topic = active_problem.step_title
        active_pattern = active_problem.pattern

        # Count total & solved in this specific pattern
        pattern_problems = [
            p for p in all_problems 
            if p.step_title == active_topic and p.pattern == active_pattern
        ]
        total_in_pattern = len(pattern_problems)
        solved_in_pattern = len([p for p in pattern_problems if p.id in solved_ids])

        progress = PatternProgress(
            pattern_name=active_pattern,
            topic=active_topic,
            total_problems=total_in_pattern,
            solved_problems=solved_in_pattern,
            is_completed=(solved_in_pattern >= total_in_pattern)
        )

        return active_topic, active_pattern, progress

    async def get_daily_problem(self, user_id: int) -> Tuple[Problem, bool, bool]:
        """
        Returns (problem, is_already_solved, is_repeated_from_yesterday) for today's assignment.
        Rule: If yesterday's problem was NOT completed/skipped, it REPEATS today until conquered.
        """
        today_str = date.today().isoformat()
        solved_ids = await self.repository.get_solved_ids(user_id)
        assignment = await self.repository.get_daily_assignment(user_id, today_str)

        # 1. If today already has an assigned problem, return it (locked for the day)
        if assignment:
            pid = assignment["problem_id"]
            p = self.primary_source.get_problem_by_id(pid)
            if p:
                is_done = bool(assignment.get("completed", 0)) or (pid in solved_ids)
                return p, is_done, False

        # 2. Check the most recent past assignment: Was it left unfinished?
        latest = await self.repository.get_latest_assignment(user_id)
        if latest and latest.get("assigned_date") != today_str:
            past_pid = latest["problem_id"]
            if past_pid not in solved_ids:
                past_problem = self.primary_source.get_problem_by_id(past_pid)
                if past_problem:
                    # Roll it forward to today so it is repeated!
                    await self.repository.set_daily_assignment(user_id, past_problem.id, today_str)
                    return past_problem, False, True

        # 3. Otherwise pick the next unsolved problem in sequence
        p = await self.get_next_problem(user_id)
        if p:
            await self.repository.set_daily_assignment(user_id, p.id, today_str)
            return p, False, False

        raise ValueError("All problems in the curriculum are already solved!")

    async def get_next_problem(self, user_id: int) -> Optional[Problem]:
        """
        Fetches the next uncompleted problem in sequence (used for fast-tracking).
        """
        solved_ids = await self.repository.get_solved_ids(user_id)
        for p in self.primary_source.get_all_problems():
            if p.id not in solved_ids:
                return p
        return None

    async def fast_track_next_pattern(self, user_id: int) -> Tuple[str, Optional[Problem]]:
        """
        Skips any remaining problems in the current pattern and jumps immediately to the next pattern.
        Returns: (new_pattern_name, first_problem_of_new_pattern)
        """
        solved_ids = await self.repository.get_solved_ids(user_id)
        all_problems = self.primary_source.get_all_problems()

        active_p = None
        for p in all_problems:
            if p.id not in solved_ids:
                active_p = p
                break

        if not active_p:
            return "Curriculum Complete", None

        curr_topic = active_p.step_title
        curr_pattern = active_p.pattern

        # Find the first problem from a DIFFERENT pattern
        next_pattern_problem = None
        for p in all_problems:
            if p.order > active_p.order:
                if p.step_title != curr_topic or p.pattern != curr_pattern:
                    next_pattern_problem = p
                    break

        if next_pattern_problem:
            # Mark skipped problems in the abandoned pattern
            for p in all_problems:
                if p.step_title == curr_topic and p.pattern == curr_pattern and p.id not in solved_ids:
                    from core.models.user import ProgressRecord
                    await self.repository.save_progress(ProgressRecord(
                        user_id=user_id,
                        problem_id=p.id,
                        slug=p.lc_slug or p.id,
                        status="SKIPPED",
                        solved_at=datetime.now().isoformat(),
                        source="MANUAL"
                    ))

            # Update today's assignment to point to this new problem
            today_str = date.today().isoformat()
            await self.repository.set_daily_assignment(user_id, next_pattern_problem.id, today_str)
            return next_pattern_problem.pattern, next_pattern_problem

        return "Curriculum Complete", None

    def get_pattern_note(self, pattern_name: str) -> Optional[PatternNote]:
        clean = pattern_name.strip().lower()
        # Direct or fuzzy match
        for k, note in self._pattern_notes.items():
            if k in clean or clean in k:
                return note
        return None

    async def get_extra_drills(self, user_id: int, limit: int = 3) -> List[Problem]:
        """
        Fetches extra drill problems matching the user's active pattern.
        """
        topic, pattern, _ = await self.get_active_pattern_info(user_id)
        if self.extra_source:
            return await self.extra_source.fetch_extra_by_pattern(pattern, topic, limit=limit)
        return []
