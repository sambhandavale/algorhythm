import aiosqlite
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Set, Tuple
from config import DATABASE_PATH, DEFAULT_REMINDER_HOUR, DEFAULT_REMINDER_MINUTE, DEFAULT_CHANNEL_ID

class Database:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = str(db_path)

    async def init_db(self):
        """Creates the tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    leetcode_username TEXT,
                    channel_id INTEGER DEFAULT 0,
                    reminder_hour INTEGER DEFAULT 8,
                    reminder_minute INTEGER DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    last_active_date TEXT,
                    preferred_step INTEGER
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS problem_progress (
                    user_id INTEGER,
                    problem_id TEXT,
                    slug TEXT,
                    status TEXT, -- 'SOLVED' or 'SKIPPED'
                    solved_at TEXT,
                    source TEXT, -- 'LEETCODE' or 'MANUAL'
                    PRIMARY KEY (user_id, problem_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS daily_assignments (
                    user_id INTEGER,
                    problem_id TEXT,
                    assigned_date TEXT, -- 'YYYY-MM-DD'
                    completed INTEGER DEFAULT 0,
                    completed_at TEXT,
                    PRIMARY KEY (user_id, assigned_date)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS revision_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    problem_id TEXT,
                    due_date TEXT, -- 'YYYY-MM-DD'
                    interval_day INTEGER,
                    completed INTEGER DEFAULT 0
                )
            """)

            await db.commit()

    async def get_user(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_or_create_user(self, user_id: int) -> dict:
        user = await self.get_user(user_id)
        if not user:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO users (user_id, reminder_hour, reminder_minute, channel_id)
                    VALUES (?, ?, ?, ?)
                """, (user_id, DEFAULT_REMINDER_HOUR, DEFAULT_REMINDER_MINUTE, DEFAULT_CHANNEL_ID))
                await db.commit()
            user = await self.get_user(user_id)
        return user

    async def set_leetcode_username(self, user_id: int, username: str):
        await self.get_or_create_user(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET leetcode_username = ? WHERE user_id = ?", (username, user_id))
            await db.commit()

    async def set_user_channel(self, user_id: int, channel_id: int):
        await self.get_or_create_user(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET channel_id = ? WHERE user_id = ?", (channel_id, user_id))
            await db.commit()

    async def set_user_reminder(self, user_id: int, hour: int, minute: int):
        await self.get_or_create_user(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET reminder_hour = ?, reminder_minute = ? WHERE user_id = ?
            """, (hour, minute, user_id))
            await db.commit()

    async def get_solved_problem_ids(self, user_id: int) -> Set[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT problem_id FROM problem_progress 
                WHERE user_id = ? AND status IN ('SOLVED', 'SKIPPED')
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return {row[0] for row in rows}

    async def get_all_solved_details(self, user_id: int) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM problem_progress WHERE user_id = ? AND status = 'SOLVED'
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def mark_problem_solved(self, user_id: int, problem_id: str, slug: str, source: str = "MANUAL") -> Tuple[int, int]:
        """Marks problem as solved, updates streak, returns (current_streak, longest_streak)."""
        await self.get_or_create_user(user_id)
        now_str = datetime.now().isoformat()
        today_str = date.today().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            # 1. Upsert problem progress
            await db.execute("""
                INSERT INTO problem_progress (user_id, problem_id, slug, status, solved_at, source)
                VALUES (?, ?, ?, 'SOLVED', ?, ?)
                ON CONFLICT(user_id, problem_id) DO UPDATE SET
                    status = 'SOLVED',
                    solved_at = excluded.solved_at,
                    source = excluded.source
            """, (user_id, problem_id, slug, now_str, source))

            # 2. Mark daily assignment as completed if matching
            await db.execute("""
                UPDATE daily_assignments 
                SET completed = 1, completed_at = ?
                WHERE user_id = ? AND problem_id = ?
            """, (now_str, user_id, problem_id))

            await db.commit()

        # 3. Update streak
        return await self._update_streak(user_id, today_str)

    async def mark_problem_skipped(self, user_id: int, problem_id: str, slug: str):
        now_str = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO problem_progress (user_id, problem_id, slug, status, solved_at, source)
                VALUES (?, ?, ?, 'SKIPPED', ?, 'MANUAL')
                ON CONFLICT(user_id, problem_id) DO UPDATE SET
                    status = 'SKIPPED',
                    solved_at = excluded.solved_at
            """, (user_id, problem_id, slug, now_str))
            await db.commit()

    async def _update_streak(self, user_id: int, today_str: str) -> Tuple[int, int]:
        user = await self.get_user(user_id)
        last_active = user.get("last_active_date")
        current_streak = user.get("current_streak", 0)
        longest_streak = user.get("longest_streak", 0)

        today = date.today()

        if last_active:
            last_date = date.fromisoformat(last_active)
            delta = (today - last_date).days
            if delta == 0:
                # Already solved something today, streak stays the same
                return current_streak, longest_streak
            elif delta == 1:
                # Solved yesterday, streak increments!
                current_streak += 1
            else:
                # Gap > 1 day, streak resets to 1
                current_streak = 1
        else:
            current_streak = 1

        if current_streak > longest_streak:
            longest_streak = current_streak

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET current_streak = ?, longest_streak = ?, last_active_date = ?
                WHERE user_id = ?
            """, (current_streak, longest_streak, today_str, user_id))
            await db.commit()

        return current_streak, longest_streak

    async def get_daily_assignment(self, user_id: int, assigned_date: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM daily_assignments WHERE user_id = ? AND assigned_date = ?
            """, (user_id, assigned_date)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def set_daily_assignment(self, user_id: int, problem_id: str, assigned_date: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO daily_assignments (user_id, problem_id, assigned_date, completed)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(user_id, assigned_date) DO UPDATE SET
                    problem_id = excluded.problem_id
            """, (user_id, problem_id, assigned_date))
            await db.commit()

    async def schedule_revision(self, user_id: int, problem_id: str, intervals: List[int] = [3, 7, 21]):
        today = date.today()
        async with aiosqlite.connect(self.db_path) as db:
            for interval in intervals:
                due = (today + timedelta(days=interval)).isoformat()
                await db.execute("""
                    INSERT INTO revision_queue (user_id, problem_id, due_date, interval_day, completed)
                    VALUES (?, ?, ?, ?, 0)
                """, (user_id, problem_id, due, interval))
            await db.commit()

    async def get_due_revisions(self, user_id: int, today_str: str) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM revision_queue 
                WHERE user_id = ? AND due_date <= ? AND completed = 0
            """, (user_id, today_str)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_all_active_users(self) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE channel_id > 0") as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
