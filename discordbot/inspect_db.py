import sqlite3
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

def inspect():
    conn = sqlite3.connect("data/bot.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 60)
    print("👤 USER PROFILE:")
    print("=" * 60)
    for row in cursor.execute("SELECT * FROM users"):
        d = dict(row)
        for k, v in d.items():
            print(f"  • {k:22}: {v}")

    print("\n" + "=" * 60)
    print("📚 PROBLEM PROGRESS (Last 10 Records):")
    print("=" * 60)
    rows = list(cursor.execute("SELECT * FROM problem_progress ORDER BY solved_at DESC LIMIT 10"))
    if not rows:
        print("  (No problems recorded yet)")
    for r in rows:
        d = dict(r)
        print(f"  • [{d['status']:7}] Problem ID: {d['problem_id']:10} | Via: {d['source']:8} | At: {d['solved_at']}")

    print("\n" + "=" * 60)
    print("🎯 TODAY'S ASSIGNMENT:")
    print("=" * 60)
    for r in cursor.execute("SELECT * FROM daily_assignments"):
        d = dict(r)
        status = "COMPLETED ✅" if d["completed"] else "PENDING ⏳"
        print(f"  • Date: {d['assigned_date']} | Problem ID: {d['problem_id']} | Status: {status}")
    print("=" * 60)

if __name__ == "__main__":
    inspect()
