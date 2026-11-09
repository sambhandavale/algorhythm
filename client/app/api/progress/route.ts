import { NextRequest, NextResponse } from "next/server";
import { db, initDb } from "@/lib/db";

export async function GET(req: NextRequest) {
  try {
    await initDb();
    const { searchParams } = new URL(req.url);
    let userId = searchParams.get("user_id");

    // If no user_id is explicitly passed, dynamically pick the first registered user
    if (!userId) {
      const firstUser = await db.execute("SELECT CAST(user_id AS TEXT) as user_id FROM users LIMIT 1");
      if (firstUser.rows.length > 0) {
        userId = firstUser.rows[0].user_id as string;
      } else {
        userId = "1";
      }
    }

    // Cast 64-bit snowflake integers to TEXT to prevent JS Number overflow
    const userRes = await db.execute({
      sql: `
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
        WHERE CAST(user_id AS TEXT) = ?
      `,
      args: [userId],
    });
    const user = userRes.rows[0] || null;

    // Fetch solved problem IDs
    const progressRes = await db.execute({
      sql: "SELECT problem_id, status FROM problem_progress WHERE CAST(user_id AS TEXT) = ?",
      args: [userId],
    });

    const solvedIds: string[] = [];
    const skippedIds: string[] = [];

    for (const row of progressRes.rows) {
      if (row.status === "SOLVED") {
        solvedIds.push(row.problem_id as string);
      } else if (row.status === "SKIPPED") {
        skippedIds.push(row.problem_id as string);
      }
    }

    return NextResponse.json({
      user,
      solvedIds,
      skippedIds,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    await initDb();
    const body = await req.json();
    let { user_id, problem_id, status, slug } = body;

    if (!user_id) {
      const firstUser = await db.execute("SELECT CAST(user_id AS TEXT) as user_id FROM users LIMIT 1");
      user_id = firstUser.rows.length > 0 ? (firstUser.rows[0].user_id as string) : "1";
    }
    const userId = user_id;
    const now = new Date().toISOString();

    if (status === "UNSOLVED") {
      await db.execute({
        sql: "DELETE FROM problem_progress WHERE CAST(user_id AS TEXT) = ? AND problem_id = ?",
        args: [userId, problem_id],
      });
    } else {
      await db.execute({
        sql: `
          INSERT INTO problem_progress (user_id, problem_id, slug, status, solved_at, source)
          VALUES (?, ?, ?, 'SOLVED', ?, 'MANUAL_WEB')
          ON CONFLICT(user_id, problem_id) DO UPDATE SET
            status = 'SOLVED',
            solved_at = excluded.solved_at,
            source = excluded.source
        `,
        args: [userId, problem_id, slug || problem_id, now],
      });

      await db.execute({
        sql: "UPDATE daily_assignments SET completed = 1, completed_at = ? WHERE CAST(user_id AS TEXT) = ? AND problem_id = ?",
        args: [now, userId, problem_id],
      });
    }

    return NextResponse.json({ success: true, problem_id, status });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
