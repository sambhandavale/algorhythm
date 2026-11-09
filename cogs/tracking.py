import discord
from discord import app_commands
from discord.ext import commands
from datetime import date
from database.db import Database
from services.sheet_manager import SheetManager
from services.leetcode import LeetCodeService
from ui.problem_card import create_problem_embed, ProblemCardView

def make_progress_bar(percentage: float, length: int = 10) -> str:
    filled = int(round((percentage / 100) * length))
    filled = min(length, max(0, filled))
    return "█" * filled + "░" * (length - filled)

class TrackingCog(commands.Cog):
    def __init__(self, bot: commands.Bot, db: Database, sheet_manager: SheetManager):
        self.bot = bot
        self.db = db
        self.sheet_manager = sheet_manager

    @app_commands.command(name="daily", description="Get today's DSA challenge from Striver's A2Z Sheet")
    async def daily_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id
        today_str = date.today().isoformat()

        # Ensure user exists
        user_data = await self.db.get_or_create_user(user_id)
        solved_ids = await self.db.get_solved_problem_ids(user_id)

        # 1. Check if an assignment already exists for today
        assignment = await self.db.get_daily_assignment(user_id, today_str)
        problem = None
        is_already_solved = False

        if assignment:
            problem = self.sheet_manager.get_problem_by_id(assignment["problem_id"])
            is_already_solved = bool(assignment.get("completed", 0))

        # 2. If no assignment or problem not found, pick the next uncompleted problem
        if not problem:
            problem = self.sheet_manager.get_next_problem(solved_ids)
            if not problem:
                await interaction.followup.send(
                    "🏆 **Incredible! You have completed all 402 problems in Striver's A2Z DSA Sheet!**"
                )
                return
            await self.db.set_daily_assignment(user_id, problem["id"], today_str)

        embed = create_problem_embed(
            problem,
            user_streak=user_data.get("current_streak", 0),
            is_solved=is_already_solved
        )
        view = ProblemCardView(self.db, self.sheet_manager, problem, user_id) if not is_already_solved else None

        await interaction.followup.send(
            content=f"👋 Hey <@{user_id}>, here is your DSA challenge for today!",
            embed=embed,
            view=view
        )

    @app_commands.command(name="progress", description="Check your progress across Striver's A2Z DSA Sheet")
    async def progress_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id
        user_data = await self.db.get_or_create_user(user_id)
        solved_ids = await self.db.get_solved_problem_ids(user_id)

        summary = self.sheet_manager.get_progress_summary(solved_ids)
        total = summary["total"]
        solved = summary["solved"]
        pct = summary["percentage"]

        bar = make_progress_bar(pct, 12)

        embed = discord.Embed(
            title=f"📊 DSA Progress — {interaction.user.display_name}",
            color=discord.Color.blurple()
        )
        embed.description = (
            f"**Overall Completion:** `{solved}/{total}` ({pct:.1f}%)\n"
            f"`{bar}`\n\n"
            f"🔥 Current Streak: **{user_data.get('current_streak', 0)} Days** "
            f"*(Best: {user_data.get('longest_streak', 0)} Days)*\n"
        )

        # Show steps breakdown
        step_lines = []
        for step_title, stats in summary["steps"].items():
            s_solved = stats["solved"]
            s_total = stats["total"]
            s_pct = (s_solved / s_total * 100) if s_total else 0
            if s_solved > 0:
                icon = "✅" if s_solved == s_total else "🔄"
            else:
                icon = "⏳"
            step_lines.append(f"{icon} **{step_title}**: `{s_solved}/{s_total}` ({s_pct:.0f}%)")

        # Group steps into chunks for embed fields
        step_text = "\n".join(step_lines[:10])
        embed.add_field(name="📑 Step Progress (Part 1)", value=step_text, inline=False)

        if len(step_lines) > 10:
            step_text_2 = "\n".join(step_lines[10:])
            embed.add_field(name="📑 Step Progress (Part 2)", value=step_text_2, inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="set-handle", description="Link your LeetCode username for auto-verification")
    @app_commands.describe(username="Your exact LeetCode username")
    async def set_handle_command(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(ephemeral=True)
        stats = await LeetCodeService.get_user_stats(username)

        if not stats:
            await interaction.followup.send(
                f"⚠️ Could not find a LeetCode profile for `{username}`. Please check the spelling and try again!",
                ephemeral=True
            )
            return

        await self.db.set_leetcode_username(interaction.user.id, username)

        embed = discord.Embed(
            title=f"✅ LeetCode Account Linked: {stats['username']}",
            color=discord.Color.green()
        )
        embed.add_field(name="Total Solved", value=f"`{stats['total_solved']}`", inline=True)
        embed.add_field(name="Easy / Med / Hard", value=f"`{stats['easy']}` / `{stats['medium']}` / `{stats['hard']}`", inline=True)
        if stats.get("ranking"):
            embed.add_field(name="Global Ranking", value=f"#{stats['ranking']:,}", inline=True)

        embed.set_footer(text="Your submissions can now be verified automatically via [Verify LeetCode]!")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="set-channel", description="Set the current channel for your daily DSA reminder")
    async def set_channel_command(self, interaction: discord.Interaction):
        channel_id = interaction.channel_id
        await self.db.set_user_channel(interaction.user.id, channel_id)
        await interaction.response.send_message(
            f"✅ Daily problems will now be posted in <#{channel_id}>!",
            ephemeral=True
        )

    @app_commands.command(name="set-time", description="Set your daily reminder time (24-hour format, e.g. 8 0 for 8:00 AM)")
    @app_commands.describe(hour="Hour (0-23)", minute="Minute (0-59)")
    async def set_time_command(self, interaction: discord.Interaction, hour: int, minute: int):
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await interaction.response.send_message("❌ Invalid time! Hour must be 0-23 and minute must be 0-59.", ephemeral=True)
            return

        await self.db.set_user_reminder(interaction.user.id, hour, minute)
        time_str = f"{hour:02d}:{minute:02d}"
        await interaction.response.send_message(
            f"⏰ Daily reminder set to **{time_str}** every day!",
            ephemeral=True
        )

    @app_commands.command(name="streak", description="Check your current DSA solving streak")
    async def streak_command(self, interaction: discord.Interaction):
        user_data = await self.db.get_or_create_user(interaction.user.id)
        curr = user_data.get("current_streak", 0)
        best = user_data.get("longest_streak", 0)
        last = user_data.get("last_active_date") or "None yet"

        embed = discord.Embed(
            title=f"🔥 DSA Streak: {curr} Days",
            color=discord.Color.orange()
        )
        embed.add_field(name="Current Streak", value=f"**{curr} Days** 🔥", inline=True)
        embed.add_field(name="Longest Streak", value=f"**{best} Days** 🏆", inline=True)
        embed.add_field(name="Last Active", value=f"`{last}`", inline=True)

        await interaction.response.send_message(embed=embed)
