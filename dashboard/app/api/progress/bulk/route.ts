import { NextRequest, NextResponse } from "next/server";
import { db, initDb } from "@/lib/db";

export async function POST(req: NextRequest) {
  try {
    await initDb();
    const body = await req.json();
    let { user_id, problem_ids, status } = body;

    if (!user_id) {
      const firstUser = await db.execute("SELECT CAST(user_id AS TEXT) as user_id FROM users LIMIT 1");
      user_id = firstUser.rows.length > 0 ? (firstUser.rows[0].user_id as string) : "1";
    }
    const userId = user_id;
    const now = new Date().toISOString();

    if (!Array.isArray(problem_ids) || problem_ids.length === 0) {
      return NextResponse.json({ error: "No problem IDs provided" }, { status: 400 });
    }

    if (status === "UNSOLVED") {
      const placeholders = problem_ids.map(() => "?").join(",");
      await db.execute({
        sql: `DELETE FROM problem_progress WHERE CAST(user_id AS TEXT) = ? AND problem_id IN (${placeholders})`,
        args: [userId, ...problem_ids],
      });
    } else {
      const stmts = problem_ids.map((pid: string) => ({
        sql: `
          INSERT INTO problem_progress (user_id, problem_id, slug, status, solved_at, source)
          VALUES (?, ?, ?, 'SOLVED', ?, 'MANUAL_WEB')
          ON CONFLICT(user_id, problem_id) DO UPDATE SET
            status = 'SOLVED',
            solved_at = excluded.solved_at,
            source = excluded.source
        `,
        args: [userId, pid, pid, now],
      }));
      await db.batch(stmts, "write");
    }

    return NextResponse.json({ success: true, count: problem_ids.length, status });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
