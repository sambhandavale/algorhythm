import discord
from discord import app_commands
from discord.ext import commands
from core.interfaces.ai_tutor import IAITutor
from core.services.study_manager import StudyManager

class AICog(commands.Cog):
    def __init__(self, bot: commands.Bot, ai_tutor: IAITutor, study_manager: StudyManager):
        self.bot = bot
        self.ai_tutor = ai_tutor
        self.study_manager = study_manager

    @app_commands.command(name="hint", description="Ask the AI for a Socratic hint on today's problem")
    @app_commands.describe(approach="What are you currently thinking or trying?")
    async def hint_command(self, interaction: discord.Interaction, approach: str):
        await interaction.response.defer(ephemeral=True)
        try:
            problem, _ = await self.study_manager.get_daily_problem(interaction.user.id)
        except Exception:
            await interaction.followup.send("Could not identify an active problem.", ephemeral=True)
            return

        hint = await self.ai_tutor.get_socratic_hint(problem, approach)
        embed = discord.Embed(
            title=f"💡 Socratic Hint: {problem.title}",
            description=hint,
            color=discord.Color.teal()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="review", description="Ask the AI to audit your code for Time/Space complexity and edge cases")
    @app_commands.describe(code="Paste your code snippet")
    async def review_command(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer()
        try:
            problem, _ = await self.study_manager.get_daily_problem(interaction.user.id)
        except Exception:
            problem = None

        if not problem:
            problem = self.study_manager.primary_source.get_all_problems()[0]

        review = await self.ai_tutor.review_code(problem, code)
        embed = discord.Embed(
            title=f"🧐 Code Review: {problem.title}",
            description=review,
            color=discord.Color.gold()
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ask", description="Ask the AI to explain a DSA concept or algorithm")
    @app_commands.describe(question="What concept or algorithm do you want explained?")
    async def ask_command(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        _, pattern, _ = await self.study_manager.get_active_pattern_info(interaction.user.id)
        explanation = await self.ai_tutor.ask_concept(pattern, question)

        embed = discord.Embed(
            title=f"🧠 DSA Concept Explanation",
            description=explanation,
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)
