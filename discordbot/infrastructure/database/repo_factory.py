from core.interfaces.repository import IProgressRepository
from config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, DATABASE_PATH
from infrastructure.database.sqlite_repo import SQLiteRepository
from infrastructure.database.turso_repo import TursoRepository

def get_repository() -> IProgressRepository:
    """
    Returns TursoRepository if Turso credentials are configured;
    otherwise falls back to local SQLiteRepository.
    """
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        print(f"☁️ Connected to Turso Cloud Database: {TURSO_DATABASE_URL[:32]}...")
        return TursoRepository(TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)
    else:
        print(f"📁 Using local SQLite database: {DATABASE_PATH}")
        return SQLiteRepository(DATABASE_PATH)
