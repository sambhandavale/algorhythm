import { createClient } from "@libsql/client";
import path from "path";

const url = process.env.TURSO_DATABASE_URL || `file:${path.resolve(process.cwd(), "../data/bot.db")}`;
const authToken = process.env.TURSO_AUTH_TOKEN;

export const db = createClient({
  url,
  authToken,
});

export async function initDb() {
  await db.execute(`
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
  `);

  await db.execute(`
    CREATE TABLE IF NOT EXISTS problem_progress (
      user_id INTEGER,
      problem_id TEXT,
      slug TEXT,
      status TEXT,
      solved_at TEXT,
      source TEXT,
      PRIMARY KEY (user_id, problem_id)
    )
  `);

  await db.execute(`
    CREATE TABLE IF NOT EXISTS daily_assignments (
      user_id INTEGER,
      problem_id TEXT,
      assigned_date TEXT,
      completed INTEGER DEFAULT 0,
      completed_at TEXT,
      PRIMARY KEY (user_id, assigned_date)
    )
  `);
}
