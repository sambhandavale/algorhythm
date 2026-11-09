import asyncio
import sys
from config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN
from infrastructure.database.repo_factory import get_repository

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

async def inspect():
    repo = get_repository()
    await repo.init()

    print("=" * 60)
    print("👤 ACTIVE USERS:")
    print("=" * 60)
    users = await repo.get_all_active_users()
    if not users:
        print("  (No active users with configured channels)")
    for u in users:
        print(f"  • User ID: {u.user_id}")
        print(f"    - LeetCode Handle : {u.leetcode_username}")
        print(f"    - Channel ID      : {u.channel_id}")
        print(f"    - Notes Channel ID: {u.notes_channel_id}")
        print(f"    - Streak          : {u.current_streak} days (Record: {u.longest_streak})")
        print(f"    - Reminder Time   : {u.reminder_hour:02d}:{u.reminder_minute:02d}")

        solved = await repo.get_solved_ids(u.user_id)
        print(f"    - Solved Problems : {len(solved)} / 402")

    print("\n" + "=" * 60)
    if users:
        u = users[0]
        latest = await repo.get_latest_assignment(u.user_id)
        print("🎯 LATEST DAILY ASSIGNMENT:")
        print("=" * 60)
        if latest:
            status = "COMPLETED ✅" if latest.get("completed") else "PENDING ⏳"
            print(f"  • Date: {latest.get('assigned_date')} | Problem ID: {latest.get('problem_id')} | Status: {status}")
        else:
            print("  (No daily assignment recorded)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(inspect())
