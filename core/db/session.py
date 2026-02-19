"""
Асинхронная сессия БД. Инициализация таблиц при старте.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.db.base import Base
from core.db.models import User, Subscription, Account, Audience, AudienceMember, Mailing, ActivityLog  # noqa: F401

# Импорт конфига без циклического импорта бота
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db")

# Для SQLite: создать папку data в корне проекта
if "sqlite" in DATABASE_URL:
    _project_root = Path(__file__).resolve().parent.parent
    (_project_root / "data").mkdir(exist_ok=True)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    """Создать таблицы при первом запуске. Миграции для новых колонок."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Миграция: добавить role в users если нет (SQLite)
        if "sqlite" in DATABASE_URL:
            from sqlalchemy import text
            def _add_role_if_missing(sync_conn):
                cur = sync_conn.execute(text("PRAGMA table_info(users)"))
                cols = [row[1] for row in cur.fetchall()]
                if "role" not in cols:
                    sync_conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL"))
            await conn.run_sync(_add_role_if_missing)
