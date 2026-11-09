import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DATABASE_PATH = BASE_DIR / "data" / "bot.db"
SHEET_PATH = BASE_DIR / "data" / "striver_a2z.json"

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

DEFAULT_REMINDER_HOUR = int(os.getenv("DAILY_REMINDER_HOUR", 8))
DEFAULT_REMINDER_MINUTE = int(os.getenv("DAILY_REMINDER_MINUTE", 0))
DEFAULT_CHANNEL_ID = int(os.getenv("DAILY_CHANNEL_ID", 0))
