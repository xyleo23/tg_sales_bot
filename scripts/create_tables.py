"""Создать таблицы БД. Можно вызывать отдельно или при первом запуске бота."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db.session import init_db


async def run():
    await init_db()
    print("Таблицы созданы.")


if __name__ == "__main__":
    asyncio.run(run())
