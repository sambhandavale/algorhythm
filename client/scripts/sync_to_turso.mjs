import { createClient } from "@libsql/client";
import fs from "fs";
import path from "path";

// Load .env.local
const envPath = path.resolve(process.cwd(), ".env.local");
const envContent = fs.readFileSync(envPath, "utf-8");
const env = {};
envContent.split("\n").forEach((line) => {
  const [k, ...v] = line.split("=");
  if (k && v.length) env[k.trim()] = v.join("=").trim();
});

const tursoUrl = env.TURSO_DATABASE_URL;
const tursoToken = env.TURSO_AUTH_TOKEN;

console.log("Connecting to Turso:", tursoUrl);

const turso = createClient({
  url: tursoUrl,
  authToken: tursoToken,
});

async function migrate() {
  console.log("1. Initializing schema in Turso...");
  await turso.execute(`
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

  await turso.execute(`
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

  await turso.execute(`
    CREATE TABLE IF NOT EXISTS daily_assignments (
      user_id INTEGER,
      problem_id TEXT,
      assigned_date TEXT,
      completed INTEGER DEFAULT 0,
      completed_at TEXT,
      PRIMARY KEY (user_id, assigned_date)
    )
  `);

  console.log("2. Reading local SQLite data from ../data/bot.db...");
  const localDb = createClient({
    url: `file:${path.resolve(process.cwd(), "../data/bot.db")}`,
  });

  const usersRes = await localDb.execute(`
    SELECT 
      CAST(user_id AS TEXT) as user_id,
      leetcode_username,
      CAST(channel_id AS TEXT) as channel_id,
      CAST(notes_channel_id AS TEXT) as notes_channel_id,
      reminder_hour,
      reminder_minute,
      current_streak,
      longest_streak,
      last_active_date
    FROM users
  `);
  console.log(`Found ${usersRes.rows.length} users to sync.`);
  for (const u of usersRes.rows) {
    await turso.execute({
      sql: `
        INSERT INTO users (user_id, leetcode_username, channel_id, notes_channel_id, reminder_hour, reminder_minute, current_streak, longest_streak, last_active_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          leetcode_username = excluded.leetcode_username,
          channel_id = excluded.channel_id,
          notes_channel_id = excluded.notes_channel_id,
          current_streak = excluded.current_streak,
          longest_streak = excluded.longest_streak,
          last_active_date = excluded.last_active_date
      `,
      args: [
        u.user_id,
        u.leetcode_username,
        u.channel_id,
        u.notes_channel_id || 0,
        u.reminder_hour,
        u.reminder_minute,
        u.current_streak,
        u.longest_streak,
        u.last_active_date,
      ],
    });
  }

  const progressRes = await localDb.execute(`
    SELECT 
      CAST(user_id AS TEXT) as user_id,
      problem_id,
      slug,
      status,
      solved_at,
      source
    FROM problem_progress
  `);
  console.log(`Found ${progressRes.rows.length} progress records to sync.`);
  const stmts = progressRes.rows.map((p) => ({
    sql: `
      INSERT INTO problem_progress (user_id, problem_id, slug, status, solved_at, source)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(user_id, problem_id) DO UPDATE SET
        status = excluded.status,
        solved_at = excluded.solved_at,
        source = excluded.source
    `,
    args: [p.user_id, p.problem_id, p.slug, p.status, p.solved_at, p.source],
  }));

  if (stmts.length > 0) {
    await turso.batch(stmts, "write");
  }

  const assignRes = await localDb.execute(`
    SELECT 
      CAST(user_id AS TEXT) as user_id,
      problem_id,
      assigned_date,
      completed,
      completed_at
    FROM daily_assignments
  `);
  for (const a of assignRes.rows) {
    await turso.execute({
      sql: `
        INSERT INTO daily_assignments (user_id, problem_id, assigned_date, completed, completed_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, assigned_date) DO UPDATE SET
          problem_id = excluded.problem_id,
          completed = excluded.completed,
          completed_at = excluded.completed_at
      `,
      args: [a.user_id, a.problem_id, a.assigned_date, a.completed, a.completed_at],
    });
  }

  console.log("3. Verifying Turso database state...");
  const checkUsers = await turso.execute("SELECT COUNT(*) as cnt FROM users");
  const checkProgress = await turso.execute("SELECT COUNT(*) as cnt FROM problem_progress");
  console.log(`🎉 SUCCESS! Turso Cloud Database now has:`);
  console.log(`   • Users count: ${checkUsers.rows[0].cnt}`);
  console.log(`   • Problem progress records: ${checkProgress.rows[0].cnt}`);
}

migrate().catch(console.error);
