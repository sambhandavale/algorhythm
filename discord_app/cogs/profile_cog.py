import discord
from discord import app_commands
from discord.ext import commands
from core.services.study_manager import StudyManager
from services.leetcode import LeetCodeService

def make_progress_bar(percentage: float, length: int = 12) -> str:
    filled = int(round((percentage / 100) * length))
    filled = min(length, max(0, filled))
    return "█" * filled + "░" * (length - filled)

class ProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot, study_manager: StudyManager):
        self.bot = bot
        self.study_manager = study_manager

    @app_commands.command(name="progress", description="Check your progress across Striver's A2Z DSA Sheet")
    async def progress_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id
        user = await self.study_manager.repository.get_or_create_user(user_id)
        solved_ids = await self.study_manager.repository.get_solved_ids(user_id)

        all_problems = self.study_manager.primary_source.get_all_problems()
        total = len(all_problems)
        solved = len([p for p in all_problems if p.id in solved_ids])
        pct = (solved / total * 100) if total else 0
        bar = make_progress_bar(pct, 14)

        topic, pattern, pat_progress = await self.study_manager.get_active_pattern_info(user_id)

        embed = discord.Embed(
            title=f"📊 DSA Mastery Dashboard — {interaction.user.display_name}",
            color=discord.Color.blurple()
        )
        embed.description = (
            f"**Overall Sheet Progress:** `{solved}/{total}` ({pct:.1f}%)\n"
            f"`{bar}`\n\n"
            f"🔥 Current Streak: **{user.current_streak} Days** *(Record: {user.longest_streak} Days)*\n"
            f"🎯 Active Pattern: **{pattern}** ({topic}) — `{pat_progress.solved_problems}/{pat_progress.total_problems}` solved"
        )

        # Topic summary
        steps_map = {}
        for p in all_problems:
            s_title = f"Step {p.step}: {p.step_title}"
            if s_title not in steps_map:
                steps_map[s_title] = {"total": 0, "solved": 0}
            steps_map[s_title]["total"] += 1
            if p.id in solved_ids:
                steps_map[s_title]["solved"] += 1

        lines = []
        for s_title, stats in steps_map.items():
            s_solved = stats["solved"]
            s_tot = stats["total"]
            s_p = (s_solved / s_tot * 100) if s_tot else 0
            icon = "✅" if s_solved == s_tot else ("🔄" if s_solved > 0 else "⏳")
            lines.append(f"{icon} **{s_title}**: `{s_solved}/{s_tot}` ({s_p:.0f}%)")

        embed.add_field(name="📑 Step Completion", value="\n".join(lines[:10]), inline=False)
        if len(lines) > 10:
            embed.add_field(name="📑 Advanced Steps", value="\n".join(lines[10:]), inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="set-handle", description="Link your LeetCode username for auto-verification")
    @app_commands.describe(username="Your exact LeetCode username")
    async def set_handle_command(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer(ephemeral=True)
        stats = await LeetCodeService.get_user_stats(username)

        if not stats:
            await interaction.followup.send(
                f"⚠️ Could not find a LeetCode profile for `{username}`. Please check the spelling!",
                ephemeral=True
            )
            return

        user = await self.study_manager.repository.get_or_create_user(interaction.user.id)
        user.leetcode_username = username
        await self.study_manager.repository.save_user(user)

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

    @app_commands.command(name="set-daily-channel", description="Set the current channel for daily problems & extra drills")
    async def set_daily_channel_command(self, interaction: discord.Interaction):
        user = await self.study_manager.repository.get_or_create_user(interaction.user.id)
        user.channel_id = interaction.channel_id
        await self.study_manager.repository.save_user(user)
        await interaction.response.send_message(
            f"🎯 Daily problem cards will now be posted in <#{interaction.channel_id}>!",
            ephemeral=True
        )

    @app_commands.command(name="set-notes-channel", description="Set the current channel for pattern cheat sheets & notes")
    async def set_notes_channel_command(self, interaction: discord.Interaction):
        user = await self.study_manager.repository.get_or_create_user(interaction.user.id)
        user.notes_channel_id = interaction.channel_id
        await self.study_manager.repository.save_user(user)
        await interaction.response.send_message(
            f"📚 Pattern cheat sheets and templates will now be posted in <#{interaction.channel_id}>!",
            ephemeral=True
        )

    @app_commands.command(name="setup-channels", description="Auto-create dedicated DSA channels (daily-problems, pattern-notes, ai-tutor)")
    async def setup_channels_command(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command must be run inside a Discord server!", ephemeral=True)
            return

        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to run this!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Create Category
            category = await guild.create_category("📚 DSA MENTOR")
            
            daily_ch = await guild.create_text_channel("🎯-daily-problems", category=category)
            notes_ch = await guild.create_text_channel("📖-pattern-notes", category=category)
            ai_ch = await guild.create_text_channel("🧠-ai-tutor", category=category)

            # Save channels for user
            user = await self.study_manager.repository.get_or_create_user(interaction.user.id)
            user.channel_id = daily_ch.id
            user.notes_channel_id = notes_ch.id
            await self.study_manager.repository.save_user(user)

            await interaction.followup.send(
                f"🎉 **Channels created and configured successfully!**\n\n"
                f"• Daily Challenges: <#{daily_ch.id}>\n"
                f"• Pattern Cheat Sheets: <#{notes_ch.id}>\n"
                f"• AI Code Review & Doubts: <#{ai_ch.id}>\n\n"
                f"Head over to <#{daily_ch.id}> and type `/daily` to begin!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Could not auto-create channels: {e}\n"
                f"You can create channels manually and run `/set-daily-channel` and `/set-notes-channel` inside them!",
                ephemeral=True
            )

    @app_commands.command(name="set-channel", description="Set the current channel for your daily DSA reminder (Alias)")
    async def set_channel_command(self, interaction: discord.Interaction):
        await self.set_daily_channel_command(interaction)

    @app_commands.command(name="set-time", description="Set daily reminder time (24-hour format, e.g. 8 0 for 8:00 AM)")
    @app_commands.describe(hour="Hour (0-23)", minute="Minute (0-59)")
    async def set_time_command(self, interaction: discord.Interaction, hour: int, minute: int):
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            await interaction.response.send_message("❌ Invalid time! Hour must be 0-23 and minute must be 0-59.", ephemeral=True)
            return

        user = await self.study_manager.repository.get_or_create_user(interaction.user.id)
        user.reminder_hour = hour
        user.reminder_minute = minute
        await self.study_manager.repository.save_user(user)

        time_str = f"{hour:02d}:{minute:02d}"
        await interaction.response.send_message(
            f"⏰ Daily reminder set to **{time_str}** every day!",
            ephemeral=True
        )

    @app_commands.command(name="streak", description="Check your current DSA solving streak")
    async def streak_command(self, interaction: discord.Interaction):
        user = await self.study_manager.repository.get_or_create_user(interaction.user.id)
        embed = discord.Embed(title=f"🔥 DSA Streak: {user.current_streak} Days", color=discord.Color.orange())
        embed.add_field(name="Current Streak", value=f"**{user.current_streak} Days** 🔥", inline=True)
        embed.add_field(name="Longest Streak", value=f"**{user.longest_streak} Days** 🏆", inline=True)
        embed.add_field(name="Last Active", value=f"`{user.last_active_date or 'None yet'}`", inline=True)
        await interaction.response.send_message(embed=embed)
