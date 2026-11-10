import discord
from discord.ext import commands, tasks
from datetime import datetime, date
from typing import Dict
from core.services.study_manager import StudyManager
from core.services.streak_service import StreakService
from core.interfaces.verifier import ISubmissionVerifier
from core.interfaces.ai_tutor import IAITutor
from discord_app.views.problem_view import create_problem_embed, ProblemCardView

class SchedulerCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        study_manager: StudyManager,
        streak_service: StreakService,
        verifier: ISubmissionVerifier,
        ai_tutor: IAITutor
    ):
        self.bot = bot
        self.study_manager = study_manager
        self.streak_service = streak_service
        self.verifier = verifier
        self.ai_tutor = ai_tutor

        # Track last nudge hour and last insight hour per user
        self.last_nudge_hour: Dict[int, int] = {}
        self.last_insight_hour: Dict[int, int] = {}

        self.background_heartbeat.start()

    def cog_unload(self):
        self.background_heartbeat.cancel()

    @tasks.loop(minutes=1)
    async def background_heartbeat(self):
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        today_str = date.today().isoformat()

        users = await self.study_manager.repository.get_all_active_users()

        for user in users:
            user_id = user.user_id
            solved_ids = await self.study_manager.repository.get_solved_ids(user_id)

            # -------------------------------------------------------------
            # 1. MORNING DAILY PING (at reminder_hour:reminder_minute)
            # -------------------------------------------------------------
            if user.reminder_hour == current_hour and user.reminder_minute == current_minute:
                if user.channel_id:
                    channel = self.bot.get_channel(user.channel_id) or await self._fetch_channel(user.channel_id)
                    if channel:
                        try:
                            problem, is_solved, is_repeated = await self.study_manager.get_daily_problem(user_id)
                            all_problems = self.study_manager.primary_source.get_all_problems()
                            pat_problems = [
                                p for p in all_problems 
                                if p.step_title == problem.step_title and p.pattern == problem.pattern
                            ]
                            pat_solved = len([p for p in pat_problems if p.id in solved_ids])
                            progress_text = f"{pat_solved}/{len(pat_problems)} solved in {problem.pattern}"

                            embed = create_problem_embed(
                                problem,
                                user_streak=user.current_streak,
                                is_solved=False,
                                pattern_progress_text=progress_text
                            )
                            view = ProblemCardView(
                                problem, user_id, self.study_manager, self.streak_service, self.verifier, self.ai_tutor
                            )
                            repeat_prefix = "🔁 **Unfinished from Yesterday**: You didn't finish this problem yesterday, so we are keeping it today until conquered!\n" if is_repeated else ""
                            await channel.send(
                                content=f"🌅 Good morning <@{user_id}>!\n{repeat_prefix}Here is your challenge on pattern **`{problem.pattern}`**:",
                                embed=embed,
                                view=view
                            )
                        except Exception as e:
                            print(f"[Scheduler Morning Error]: {e}")
                    else:
                        print(f"[Scheduler Warning]: Channel {user.channel_id} not found for user {user_id}. Run /set-daily-channel in Discord.")

            # -------------------------------------------------------------
            # 2. EVERY 3 HOURS ACCOUNTABILITY NUDGE (Until Solved)
            # -------------------------------------------------------------
            # Only between 9:00 AM and 11:00 PM
            if 9 <= current_hour <= 23 and current_minute == 0:
                last_nudge = self.last_nudge_hour.get(user_id, -99)
                if (current_hour - last_nudge) >= 3:
                    assignment = await self.study_manager.repository.get_daily_assignment(user_id, today_str)
                    if assignment and not assignment.get("completed", 0):
                        # Check if problem is indeed still unsolved
                        pid = assignment["problem_id"]
                        if pid not in solved_ids and user.channel_id:
                            problem = self.study_manager.primary_source.get_problem_by_id(pid)
                            channel = self.bot.get_channel(user.channel_id) or await self._fetch_channel(user.channel_id)
                            if problem and channel:
                                self.last_nudge_hour[user_id] = current_hour
                                await channel.send(
                                    content=(
                                        f"⏰ **Accountability Nudge** for <@{user_id}>!\n"
                                        f"Today's problem **`{problem.title}`** (`{problem.pattern}`) is still waiting for you. "
                                        f"Protect your **{user.current_streak} Day** streak! 🔥\n"
                                        f"👉 [Click here to solve]({problem.url})"
                                    )
                                )

            # -------------------------------------------------------------
            # 3. EVERY 4 HOURS AI PATTERN INSIGHT (in #pattern-notes)
            # -------------------------------------------------------------
            # Generates fresh micro-learning pointers for the current pattern
            if 8 <= current_hour <= 23 and current_minute == 15:
                last_insight = self.last_insight_hour.get(user_id, -99)
                if (current_hour - last_insight) >= 4:
                    notes_ch_id = user.notes_channel_id
                    if notes_ch_id:
                        channel = self.bot.get_channel(notes_ch_id) or await self._fetch_channel(notes_ch_id)
                        if channel:
                            try:
                                topic, pattern, _ = await self.study_manager.get_active_pattern_info(user_id)
                                problem, _, _ = await self.study_manager.get_daily_problem(user_id)

                                insight = await self.ai_tutor.generate_pattern_insight(
                                    pattern_name=pattern,
                                    topic=topic,
                                    problem_title=problem.title
                                )

                                embed = discord.Embed(
                                    title=f"🧠 Pattern Insight: {pattern}",
                                    description=f"**Current Topic**: `{topic}` • **Active Problem**: `{problem.title}`\n\n{insight}",
                                    color=discord.Color.gold()
                                )
                                embed.set_footer(text="Automated 4-hour AI Pattern Booster • DSA Mentor")

                                self.last_insight_hour[user_id] = current_hour
                                await channel.send(embed=embed)
                            except Exception as e:
                                print(f"[Scheduler Insight Error]: {e}")

    async def _fetch_channel(self, channel_id: int):
        try:
            return await self.bot.fetch_channel(channel_id)
        except Exception:
            return None

    @background_heartbeat.before_loop
    async def before_heartbeat(self):
        await self.bot.wait_until_ready()
