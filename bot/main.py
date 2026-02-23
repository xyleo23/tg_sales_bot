"""Точка входа бота."""
import asyncio
import logging
import sys
from pathlib import Path

# Корень проекта в path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN
from bot.handlers import router
from core.db.session import init_db

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
