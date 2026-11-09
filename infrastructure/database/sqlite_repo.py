import aiosqlite
from typing import Optional, Set, List
from core.models.user import UserProfile, ProgressRecord
from core.interfaces.repository import IProgressRepository
from config import DATABASE_PATH, DEFAULT_REMINDER_HOUR, DEFAULT_REMINDER_MINUTE, DEFAULT_CHANNEL_ID

class SQLiteRepository(IProgressRepository):
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = str(db_path)

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    leetcode_username TEXT,
                    channel_id INTEGER DEFAULT 0,
                    notes_channel_id INTEGER DEFAULT 0,
                    reminder_hour INTEGER DEFAULT 8,
                    reminder_minute INTEGER DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    last_active_date TEXT,
                    active_pattern TEXT,
                    pattern_started_date TEXT
                )
            """)

            # Ensure notes_channel_id column exists if table was created previously
            try:
                await db.execute("ALTER TABLE users ADD COLUMN notes_channel_id INTEGER DEFAULT 0")
            except Exception:
                pass

            await db.execute("""
                CREATE TABLE IF NOT EXISTS problem_progress (
                    user_id INTEGER,
                    problem_id TEXT,
                    slug TEXT,
                    status TEXT,
                    solved_at TEXT,
                    source TEXT,
                    PRIMARY KEY (user_id, problem_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS daily_assignments (
                    user_id INTEGER,
                    problem_id TEXT,
                    assigned_date TEXT,
                    completed INTEGER DEFAULT 0,
                    completed_at TEXT,
                    PRIMARY KEY (user_id, assigned_date)
                )
            """)
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[UserProfile]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return UserProfile(
                    user_id=row["user_id"],
                    leetcode_username=row["leetcode_username"],
                    channel_id=row["channel_id"],
                    notes_channel_id=row["notes_channel_id"] if "notes_channel_id" in row.keys() else 0,
                    reminder_hour=row["reminder_hour"],
                    reminder_minute=row["reminder_minute"],
                    current_streak=row["current_streak"],
                    longest_streak=row["longest_streak"],
                    last_active_date=row["last_active_date"],
                    active_pattern=row["active_pattern"],
                    pattern_started_date=row["pattern_started_date"]
                )

    async def get_or_create_user(self, user_id: int) -> UserProfile:
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

    async def save_user(self, user: UserProfile):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, leetcode_username, channel_id, notes_channel_id, reminder_hour, reminder_minute,
                                  current_streak, longest_streak, last_active_date, active_pattern, pattern_started_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    leetcode_username = excluded.leetcode_username,
                    channel_id = excluded.channel_id,
                    notes_channel_id = excluded.notes_channel_id,
                    reminder_hour = excluded.reminder_hour,
                    reminder_minute = excluded.reminder_minute,
                    current_streak = excluded.current_streak,
                    longest_streak = excluded.longest_streak,
                    last_active_date = excluded.last_active_date,
                    active_pattern = excluded.active_pattern,
                    pattern_started_date = excluded.pattern_started_date
            """, (
                user.user_id, user.leetcode_username, user.channel_id, user.notes_channel_id, user.reminder_hour, user.reminder_minute,
                user.current_streak, user.longest_streak, user.last_active_date, user.active_pattern, user.pattern_started_date
            ))
            await db.commit()

    async def get_solved_ids(self, user_id: int) -> Set[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT problem_id FROM problem_progress 
                WHERE user_id = ? AND status IN ('SOLVED', 'SKIPPED')
            """, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return {row[0] for row in rows}

    async def save_progress(self, record: ProgressRecord):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO problem_progress (user_id, problem_id, slug, status, solved_at, source)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, problem_id) DO UPDATE SET
                    status = excluded.status,
                    solved_at = excluded.solved_at,
                    source = excluded.source
            """, (record.user_id, record.problem_id, record.slug, record.status, record.solved_at, record.source))

            if record.status == "SOLVED":
                await db.execute("""
                    UPDATE daily_assignments 
                    SET completed = 1, completed_at = ?
                    WHERE user_id = ? AND problem_id = ?
                """, (record.solved_at, record.user_id, record.problem_id))

            await db.commit()

    async def get_daily_assignment(self, user_id: int, date_str: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM daily_assignments WHERE user_id = ? AND assigned_date = ?
            """, (user_id, date_str)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_latest_assignment(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM daily_assignments WHERE user_id = ? ORDER BY assigned_date DESC LIMIT 1
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def set_daily_assignment(self, user_id: int, problem_id: str, date_str: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO daily_assignments (user_id, problem_id, assigned_date, completed)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(user_id, assigned_date) DO UPDATE SET
                    problem_id = excluded.problem_id
            """, (user_id, problem_id, date_str))
            await db.commit()

    async def mark_daily_completed(self, user_id: int, problem_id: str):
        from datetime import datetime
        now_str = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE daily_assignments 
                SET completed = 1, completed_at = ?
                WHERE user_id = ? AND problem_id = ?
            """, (now_str, user_id, problem_id))
            await db.commit()

    async def get_all_active_users(self) -> List[UserProfile]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE channel_id > 0") as cursor:
                rows = await cursor.fetchall()
                return [
                    UserProfile(
                        user_id=r["user_id"],
                        leetcode_username=r["leetcode_username"],
                        channel_id=r["channel_id"],
                        notes_channel_id=r["notes_channel_id"] if "notes_channel_id" in r.keys() else 0,
                        reminder_hour=r["reminder_hour"],
                        reminder_minute=r["reminder_minute"],
                        current_streak=r["current_streak"],
                        longest_streak=r["longest_streak"],
                        last_active_date=r["last_active_date"],
                        active_pattern=r["active_pattern"],
                        pattern_started_date=r["pattern_started_date"]
                    )
                    for r in rows
                ]
