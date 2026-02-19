"""Проверка: токен, getMe, отправка тестового сообщения."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import BOT_TOKEN, SUPER_ADMIN_IDS
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


async def main():
    if not BOT_TOKEN:
        print("ОШИБКА: BOT_TOKEN не задан в .env")
        return
    print(f"BOT_TOKEN: {BOT_TOKEN[:15]}... (длина {len(BOT_TOKEN)})")
    print(f"SUPER_ADMIN_IDS: {SUPER_ADMIN_IDS}")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    try:
        me = await bot.get_me()
        print(f"Бот: @{me.username} (id={me.id})")

        if SUPER_ADMIN_IDS:
            # Отправить тестовое сообщение супер-админу
            await bot.send_message(SUPER_ADMIN_IDS[0], "Бот работает. Тест.")
            print("Сообщение отправлено супер-админу.")
        else:
            print("SUPER_ADMIN_IDS пуст — сообщение не отправлено")
    except Exception as e:
        print(f"Ошибка: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
