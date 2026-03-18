"""Сессия БД."""
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "tg_sales_bot.db"

_default_url = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", _default_url)

_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
async_session_maker = async_session_factory


async def init_db() -> None:
    """Создать таблицы."""
    if DATABASE_URL.startswith("sqlite"):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
