import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from core.services.study_manager import StudyManager
from discord_app.views.notes_view import create_pattern_notes_embed

from core.interfaces.ai_tutor import IAITutor

class NotesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, study_manager: StudyManager, ai_tutor: Optional[IAITutor] = None):
        self.bot = bot
        self.study_manager = study_manager
        self.ai_tutor = ai_tutor

    @app_commands.command(name="insight", description="Generate a fresh, bite-sized AI tip/trap for your active pattern right now")
    async def insight_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id
        topic, pattern, _ = await self.study_manager.get_active_pattern_info(user_id)
        try:
            problem, _ = await self.study_manager.get_daily_problem(user_id)
            title = problem.title
        except Exception:
            title = "Pattern Practice"

        if not self.ai_tutor:
            await interaction.followup.send("AI Tutor is not configured.", ephemeral=True)
            return

        insight = await self.ai_tutor.generate_pattern_insight(
            pattern_name=pattern,
            topic=topic,
            problem_title=title
        )

        embed = discord.Embed(
            title=f"🧠 Pattern Insight: {pattern}",
            description=f"**Current Topic**: `{topic}` • **Active Problem**: `{title}`\n\n{insight}",
            color=discord.Color.gold()
        )
        embed.set_footer(text="DSA Mentor • AI Pattern Booster")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="notes", description="View cheat sheet, mental model, and code template for a pattern")
    @app_commands.describe(pattern="Specific pattern name (leave empty to view your current active pattern)")
    async def notes_command(self, interaction: discord.Interaction, pattern: Optional[str] = None):
        if not pattern:
            # Look up user's active pattern
            _, active_pat, _ = await self.study_manager.get_active_pattern_info(interaction.user.id)
            target_pattern = active_pat
        else:
            target_pattern = pattern

        note = self.study_manager.get_pattern_note(target_pattern)
        if not note:
            await interaction.response.send_message(
                f"ℹ️ No curated cheat sheet found for pattern **`{target_pattern}`** yet.\n"
                f"Available cheat sheets: `On answers`, `Logic Building`, `Sliding Window`, `DP on Subsequences`.",
                ephemeral=True
            )
            return

        embed = create_pattern_notes_embed(note)
        await interaction.response.send_message(embed=embed)
