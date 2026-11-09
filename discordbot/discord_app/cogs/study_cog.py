import discord
from discord import app_commands
from discord.ext import commands
from core.services.study_manager import StudyManager
from core.services.streak_service import StreakService
from core.interfaces.verifier import ISubmissionVerifier
from core.interfaces.ai_tutor import IAITutor
from discord_app.views.problem_view import create_problem_embed, ProblemCardView
from discord_app.views.notes_view import create_pattern_notes_embed

class StudyCog(commands.Cog):
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

    @app_commands.command(name="daily", description="Get today's scheduled DSA problem from Striver's sheet")
    async def daily_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id
        user = await self.study_manager.repository.get_or_create_user(user_id)

        try:
            problem, is_solved, is_repeated = await self.study_manager.get_daily_problem(user_id)
        except ValueError:
            await interaction.followup.send("🏆 **You have completed all problems in the curriculum!**")
            return

        # Calculate pattern progress strictly for this problem's pattern
        all_problems = self.study_manager.primary_source.get_all_problems()
        pat_problems = [
            p for p in all_problems 
            if p.step_title == problem.step_title and p.pattern == problem.pattern
        ]
        solved_ids = await self.study_manager.repository.get_solved_ids(user_id)
        pat_total = len(pat_problems)
        pat_solved = len([p for p in pat_problems if p.id in solved_ids])
        progress_text = f"{pat_solved}/{pat_total} solved in {problem.pattern}"

        embed = create_problem_embed(
            problem,
            user_streak=user.current_streak,
            is_solved=is_solved,
            pattern_progress_text=progress_text
        )
        view = ProblemCardView(
            problem, user_id, self.study_manager, self.streak_service, self.verifier, self.ai_tutor
        ) if not is_solved else None

        repeat_note = "🔁 **Unfinished from Yesterday**: Let's conquer this problem today!\n" if is_repeated else ""
        await interaction.followup.send(
            content=f"{repeat_note}👋 Hey <@{user_id}>, here is your DSA challenge for today:",
            embed=embed,
            view=view
        )

    @app_commands.command(name="next", description="Fast-track: Get the next problem in sequence right now")
    async def next_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id
        user = await self.study_manager.repository.get_or_create_user(user_id)

        problem = await self.study_manager.get_next_problem(user_id)
        if not problem:
            await interaction.followup.send("🏆 **No more unsolved problems left!**")
            return

        # Calculate pattern progress strictly for this problem's pattern
        all_problems = self.study_manager.primary_source.get_all_problems()
        pat_problems = [
            p for p in all_problems 
            if p.step_title == problem.step_title and p.pattern == problem.pattern
        ]
        solved_ids = await self.study_manager.repository.get_solved_ids(user_id)
        pat_total = len(pat_problems)
        pat_solved = len([p for p in pat_problems if p.id in solved_ids])
        progress_text = f"{pat_solved}/{pat_total} in {problem.pattern}"

        embed = create_problem_embed(
            problem,
            user_streak=user.current_streak,
            is_solved=False,
            pattern_progress_text=progress_text
        )
        view = ProblemCardView(
            problem, user_id, self.study_manager, self.streak_service, self.verifier, self.ai_tutor
        )

        await interaction.followup.send(
            content=f"⚡ **Fast-Track Mode**: Here is your next problem!",
            embed=embed,
            view=view
        )

    @app_commands.command(name="next-pattern", description="Fast-track: Skip remaining problems and jump to the next pattern")
    async def next_pattern_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id
        user = await self.study_manager.repository.get_or_create_user(user_id)

        new_pattern, problem = await self.study_manager.fast_track_next_pattern(user_id)
        if not problem:
            await interaction.followup.send("🏆 You have completed or passed all patterns in the sheet!")
            return

        # Post cheat sheet to notes channel if configured, otherwise current channel
        note = self.study_manager.get_pattern_note(new_pattern)
        if note:
            notes_embed = create_pattern_notes_embed(note)
            target_ch = None
            if user.notes_channel_id:
                target_ch = self.bot.get_channel(user.notes_channel_id)
            if not target_ch:
                target_ch = interaction.channel

            await target_ch.send(
                content=f"🎓 **New Pattern Unlocked: `{new_pattern}`**",
                embed=notes_embed
            )

        embed = create_problem_embed(problem, user_streak=user.current_streak, is_solved=False)
        view = ProblemCardView(
            problem, user_id, self.study_manager, self.streak_service, self.verifier, self.ai_tutor
        )

        await interaction.followup.send(
            content=f"🚀 **Advanced to New Pattern: `{new_pattern}`**!\nHere is the first problem:",
            embed=embed,
            view=view
        )

    @app_commands.command(name="extra", description="Get 2-3 extra bonus drill problems on your current pattern")
    async def extra_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id
        user = await self.study_manager.repository.get_or_create_user(user_id)

        topic, pattern, _ = await self.study_manager.get_active_pattern_info(user_id)
        drills = await self.study_manager.get_extra_drills(user_id, limit=3)

        if not drills:
            await interaction.followup.send(
                f"ℹ️ No extra drill problems found for pattern **`{pattern}`** right now. Try `/daily` or `/next`!"
            )
            return

        await interaction.followup.send(
            content=f"🎯 **Extra Drills for `{pattern}`** ({topic}):\nHere are {len(drills)} bonus problems to solidify this pattern:"
        )

        for p in drills:
            embed = create_problem_embed(p, user_streak=user.current_streak, is_solved=False)
            view = ProblemCardView(
                p, user_id, self.study_manager, self.streak_service, self.verifier, self.ai_tutor
            )
            await interaction.channel.send(embed=embed, view=view)
