import discord
from discord.ext import commands, tasks
from datetime import datetime, date
from database.db import Database
from services.sheet_manager import SheetManager
from ui.problem_card import create_problem_embed, ProblemCardView

class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database, sheet_manager: SheetManager):
        self.bot = bot
        self.db = db
        self.sheet_manager = sheet_manager
        self.daily_check_loop.start()

    def cog_unload(self):
        self.daily_check_loop.cancel()

    @tasks.loop(minutes=1)
    async def daily_check_loop(self):
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        today_str = date.today().isoformat()

        users = await self.db.get_all_active_users()
        for user in users:
            u_hour = user.get("reminder_hour", 8)
            u_min = user.get("reminder_minute", 0)

            # Match hour and minute
            if u_hour == current_hour and u_min == current_minute:
                user_id = user["user_id"]
                channel_id = user.get("channel_id")

                if not channel_id:
                    continue

                # Check if already assigned today
                assignment = await self.db.get_daily_assignment(user_id, today_str)
                if assignment:
                    continue  # Already assigned today

                channel = self.bot.get_channel(channel_id)
                if not channel:
                    try:
                        channel = await self.bot.fetch_channel(channel_id)
                    except Exception:
                        continue

                # Pick next problem
                solved_ids = await self.db.get_solved_problem_ids(user_id)
                problem = self.sheet_manager.get_next_problem(solved_ids)

                if not problem:
                    continue

                await self.db.set_daily_assignment(user_id, problem["id"], today_str)

                embed = create_problem_embed(
                    problem,
                    user_streak=user.get("current_streak", 0),
                    is_solved=False
                )
                view = ProblemCardView(self.db, self.sheet_manager, problem, user_id)

                # Check for due revisions
                due_revisions = await self.db.get_due_revisions(user_id, today_str)
                rev_text = ""
                if due_revisions:
                    rev_p = self.sheet_manager.get_problem_by_id(due_revisions[0]["problem_id"])
                    if rev_p:
                        rev_text = f"\n🔁 **Revision Due Today:** `{rev_p['title']}` ({rev_p.get('url', '')})"

                await channel.send(
                    content=f"🌅 Good morning <@{user_id}>! Here is today's Striver A2Z challenge:{rev_text}",
                    embed=embed,
                    view=view
                )

    @daily_check_loop.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()
