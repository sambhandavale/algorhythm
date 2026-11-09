import aiohttp
from typing import Optional, Set, List, Dict, Any
from datetime import datetime
from core.models.user import UserProfile, ProgressRecord
from core.interfaces.repository import IProgressRepository
from config import DEFAULT_REMINDER_HOUR, DEFAULT_REMINDER_MINUTE, DEFAULT_CHANNEL_ID

def to_turso_arg(val: Any) -> dict:
    if val is None:
        return {"type": "null"}
    elif isinstance(val, bool):
        return {"type": "integer", "value": "1" if val else "0"}
    elif isinstance(val, int):
        return {"type": "integer", "value": str(val)}
    elif isinstance(val, float):
        return {"type": "float", "value": val}
    else:
        return {"type": "text", "value": str(val)}

def parse_turso_val(val_obj: Any) -> Any:
    if not isinstance(val_obj, dict):
        return val_obj
    t = val_obj.get("type")
    v = val_obj.get("value")
    if t == "null" or v is None:
        return None
    elif t == "integer":
        return int(v)
    elif t == "float":
        return float(v)
    elif t == "text":
        return str(v)
    return v

class TursoRepository(IProgressRepository):
    def __init__(self, database_url: str, auth_token: str):
        # Convert libsql:// or http:// to https://
        clean_url = database_url.replace("libsql://", "https://")
        if not clean_url.startswith("http"):
            clean_url = "https://" + clean_url
        if not clean_url.endswith("/v2/pipeline"):
            clean_url = clean_url.rstrip("/") + "/v2/pipeline"
        self.endpoint = clean_url
        self.auth_token = auth_token

    async def _execute(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        args = [to_turso_arg(p) for p in params]
        body = {
            "requests": [
                {
                    "type": "execute",
                    "stmt": {
                        "sql": sql,
                        "args": args
                    }
                }
            ]
        }
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint, json=body, headers=headers, timeout=12) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Turso API returned {resp.status}: {text}")
                data = await resp.json()
                results = data.get("results", [])
                if not results or results[0].get("type") == "error":
                    err = results[0].get("error", {}) if results else "No result"
                    raise RuntimeError(f"Turso query error: {err}")
                
                result = results[0].get("response", {}).get("result", {})
                cols = [c.get("name") for c in result.get("cols", [])]
                rows = result.get("rows", [])
                return [
                    {cols[i]: parse_turso_val(r[i]) for i in range(len(cols))}
                    for r in rows
                ]

    async def init(self):
        await self._execute("""
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
        try:
            await self._execute("ALTER TABLE users ADD COLUMN notes_channel_id INTEGER DEFAULT 0")
        except Exception:
            pass

        await self._execute("""
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

        await self._execute("""
            CREATE TABLE IF NOT EXISTS daily_assignments (
                user_id INTEGER,
                problem_id TEXT,
                assigned_date TEXT,
                completed INTEGER DEFAULT 0,
                completed_at TEXT,
                PRIMARY KEY (user_id, assigned_date)
            )
        """)

    async def get_user(self, user_id: int) -> Optional[UserProfile]:
        rows = await self._execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not rows:
            return None
        row = rows[0]
        return UserProfile(
            user_id=row["user_id"],
            leetcode_username=row.get("leetcode_username"),
            channel_id=row.get("channel_id") or 0,
            notes_channel_id=row.get("notes_channel_id") or 0,
            reminder_hour=row.get("reminder_hour", 8),
            reminder_minute=row.get("reminder_minute", 0),
            current_streak=row.get("current_streak", 0),
            longest_streak=row.get("longest_streak", 0),
            last_active_date=row.get("last_active_date"),
            active_pattern=row.get("active_pattern"),
            pattern_started_date=row.get("pattern_started_date")
        )

    async def get_or_create_user(self, user_id: int) -> UserProfile:
        user = await self.get_user(user_id)
        if not user:
            await self._execute("""
                INSERT INTO users (user_id, reminder_hour, reminder_minute, channel_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, DEFAULT_REMINDER_HOUR, DEFAULT_REMINDER_MINUTE, DEFAULT_CHANNEL_ID))
            user = await self.get_user(user_id)
        return user

    async def save_user(self, user: UserProfile):
        await self._execute("""
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

    async def get_solved_ids(self, user_id: int) -> Set[str]:
        rows = await self._execute("""
            SELECT problem_id FROM problem_progress 
            WHERE user_id = ? AND status IN ('SOLVED', 'SKIPPED')
        """, (user_id,))
        return {r["problem_id"] for r in rows if "problem_id" in r}

    async def save_progress(self, record: ProgressRecord):
        await self._execute("""
            INSERT INTO problem_progress (user_id, problem_id, slug, status, solved_at, source)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, problem_id) DO UPDATE SET
                status = excluded.status,
                solved_at = excluded.solved_at,
                source = excluded.source
        """, (record.user_id, record.problem_id, record.slug, record.status, record.solved_at, record.source))

        if record.status == "SOLVED":
            await self._execute("""
                UPDATE daily_assignments 
                SET completed = 1, completed_at = ?
                WHERE user_id = ? AND problem_id = ?
            """, (record.solved_at, record.user_id, record.problem_id))

    async def get_daily_assignment(self, user_id: int, date_str: str) -> Optional[dict]:
        rows = await self._execute("""
            SELECT * FROM daily_assignments WHERE user_id = ? AND assigned_date = ?
        """, (user_id, date_str))
        return rows[0] if rows else None

    async def get_latest_assignment(self, user_id: int) -> Optional[dict]:
        rows = await self._execute("""
            SELECT * FROM daily_assignments WHERE user_id = ? ORDER BY assigned_date DESC LIMIT 1
        """, (user_id,))
        return rows[0] if rows else None

    async def set_daily_assignment(self, user_id: int, problem_id: str, date_str: str):
        await self._execute("""
            INSERT INTO daily_assignments (user_id, problem_id, assigned_date, completed)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(user_id, assigned_date) DO UPDATE SET
                problem_id = excluded.problem_id
        """, (user_id, problem_id, date_str))

    async def mark_daily_completed(self, user_id: int, problem_id: str):
        now_str = datetime.now().isoformat()
        await self._execute("""
            UPDATE daily_assignments 
            SET completed = 1, completed_at = ?
            WHERE user_id = ? AND problem_id = ?
        """, (now_str, user_id, problem_id))

    async def get_all_active_users(self) -> List[UserProfile]:
        rows = await self._execute("SELECT * FROM users WHERE channel_id > 0")
        return [
            UserProfile(
                user_id=r["user_id"],
                leetcode_username=r.get("leetcode_username"),
                channel_id=r.get("channel_id") or 0,
                notes_channel_id=r.get("notes_channel_id") or 0,
                reminder_hour=r.get("reminder_hour", 8),
                reminder_minute=r.get("reminder_minute", 0),
                current_streak=r.get("current_streak", 0),
                longest_streak=r.get("longest_streak", 0),
                last_active_date=r.get("last_active_date"),
                active_pattern=r.get("active_pattern"),
                pattern_started_date=r.get("pattern_started_date")
            )
            for r in rows
        ]
