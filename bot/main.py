"""
Точка входа бота «Рассылка + поиск клиентов» в Telegram.
Запуск: python -m bot.main
"""
# Загрузка .env ДО любых импортов (из любой директории запуска)
import os
from pathlib import Path
from dotenv import load_dotenv
_env_paths = [
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
    Path.cwd() / "tg_sales_bot" / ".env",
]
for p in _env_paths:
    if p.exists():
        load_dotenv(p)
        break

import asyncio
import logging
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger as loguru_logger

from bot.config import BOT_TOKEN, LOG_LEVEL, LOG_FILE, YOOKASSA_SHOP_ID, YOOKASSA_WEBHOOK_PORT
from bot.middlewares import DbSessionMiddleware
from bot.handlers import setup_routers
from core.db.session import init_db

# Логирование: в файл при LOG_FILE
if LOG_FILE:
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    loguru_logger.add(
        LOG_FILE,
        rotation="10 MB",
        retention="7 days",
        level=LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} — {message}",
    )
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(DbSessionMiddleware())
dp.callback_query.middleware(DbSessionMiddleware())
setup_routers(dp)


@dp.error()
async def global_error_handler(event):
    """Глобальный обработчик ошибок."""
    logger.exception("Unhandled error: %s", event.exception)


async def start_webhook_server(app, port: int) -> None:
    """Запуск aiohttp-сервера вебхуков ЮKassa как фоновой задачи."""
    from aiohttp import web
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Webhook ЮKassa запущен на порту %s", port)
    while True:
        await asyncio.sleep(3600)


async def main():
    if not BOT_TOKEN:
        logger.error("Задайте BOT_TOKEN в .env")
        return
    await init_db()
    me = await bot.get_me()
    from bot.config import TG_API_ID
    print(f"Бот @{me.username} запущен. TG_API: {'OK' if TG_API_ID else 'NO'}")
    logger.info("Бот запущен (polling)")

    # Webhook ЮKassa — запуск в фоне, чтобы не блокировать polling
    if YOOKASSA_SHOP_ID and YOOKASSA_WEBHOOK_PORT:
        from core.payment_webhook import create_webhook_app
        app = create_webhook_app()
        asyncio.create_task(start_webhook_server(app, YOOKASSA_WEBHOOK_PORT))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
