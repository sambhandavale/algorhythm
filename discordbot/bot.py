import asyncio
import sys
import json
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import discord
from discord.ext import commands

from config import (
    DISCORD_TOKEN,
    DATABASE_PATH,
    SHEET_PATH,
    HOST,
    PORT,
    ENABLE_HEALTH_SERVER
)
from core.models.pattern import PatternNote
from infrastructure.database.repo_factory import get_repository
from infrastructure.sources.striver_adapter import StriverSheetAdapter
from infrastructure.sources.leetcode_adapter import LeetCodeAdapter
from infrastructure.verifiers.leetcode_verifier import LeetCodeVerifier
from infrastructure.ai.ai_factory import get_ai_tutor
from infrastructure.web import start_health_server
from core.services.study_manager import StudyManager
from core.services.streak_service import StreakService

from discord_app.cogs.study_cog import StudyCog
from discord_app.cogs.notes_cog import NotesCog
from discord_app.cogs.ai_cog import AICog
from discord_app.cogs.profile_cog import ProfileCog
from discord_app.cogs.scheduler_cog import SchedulerCog

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dependency Injection Container
repository = get_repository()
primary_source = StriverSheetAdapter(SHEET_PATH)
verifier = LeetCodeVerifier()
ai_tutor = get_ai_tutor()
extra_source = LeetCodeAdapter(ai_tutor=ai_tutor)

study_manager = StudyManager(
    primary_source=primary_source,
    repository=repository,
    extra_source=extra_source
)
streak_service = StreakService(repository=repository)

# Load curated pattern notes
notes_path = Path(__file__).resolve().parent / "data" / "pattern_notes.json"
if notes_path.exists():
    try:
        with open(notes_path, "r", encoding="utf-8") as f:
            notes_data = json.load(f)
            for item in notes_data:
                study_manager.register_pattern_note(PatternNote(**item))
    except Exception as e:
        print(f"Warning: Failed to load pattern notes: {e}")

@bot.event
async def on_ready():
    provider_name = type(ai_tutor.primary).__name__.replace("Adapter", "")
    print("=" * 60)
    print(f"🤖 Bot online as {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
    print(f"📚 Striver A2Z Curriculum: {len(primary_source.get_all_problems())} problems loaded")
    print(f"🧠 Active AI Provider: {provider_name}")
    print(f"📖 Pattern Notes Registered: {len(study_manager._pattern_notes)} cheat sheets")
    
    # Sync Slash Commands
    try:
        synced = await bot.tree.sync()
        print(f"✨ Successfully synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
    print("=" * 60)

async def main():
    if not DISCORD_TOKEN or DISCORD_TOKEN == "your_bot_token_here":
        print("=" * 60)
        print("⚠️ ERROR: No DISCORD_TOKEN found in .env file!")
        print("Please edit .env and paste your Discord bot token:")
        print("DISCORD_TOKEN=your_actual_token_here")
        print("=" * 60)
        sys.exit(1)

    # Initialize Repository Storage
    await repository.init()

    # Register Cogs
    await bot.add_cog(StudyCog(bot, study_manager, streak_service, verifier, ai_tutor))
    await bot.add_cog(NotesCog(bot, study_manager, ai_tutor))
    await bot.add_cog(AICog(bot, ai_tutor, study_manager))
    await bot.add_cog(ProfileCog(bot, study_manager))
    await bot.add_cog(SchedulerCog(bot, study_manager, streak_service, verifier, ai_tutor))

    # Start Health Check Server (for Render / Railway / uptime pingers)
    runner = None
    if ENABLE_HEALTH_SERVER:
        runner = await start_health_server(bot, host=HOST, port=PORT)

    # Start Bot
    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    finally:
        if runner:
            await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
