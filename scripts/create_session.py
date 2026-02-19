"""
Создание .session файла для Telethon (парсер, рассылка).
Запуск: py scripts/create_session.py [--name test] [--phone +79991234567]
Без аргументов — интерактивный ввод.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon import TelegramClient
from bot.config import TG_API_ID, TG_API_HASH, SESSIONS_DIR


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="", help="Имя сессии (например test)")
    parser.add_argument("--phone", default="", help="Номер телефона (+79991234567)")
    parser.add_argument("--code", default="", help="Код из Telegram (если уже пришёл)")
    args = parser.parse_args()

    if not TG_API_ID or not TG_API_HASH:
        print("ОШИБКА: Задайте TG_API_ID и TG_API_HASH в .env")
        return

    name = (args.name or input("Введите имя сессии (латиница, например main): ").strip() or "main")
    name = "".join(c for c in name if c.isalnum() or c == "_")[:15] or "session"

    session_path = SESSIONS_DIR / name
    client = TelegramClient(str(session_path), TG_API_ID, TG_API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        phone = args.phone or input("Введите номер телефона (формат +79991234567): ").strip()
        await client.send_code_request(phone)
        code = args.code or input("Vvedite kod iz Telegram: ").strip()
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            if "Two-step" in str(e) or "2FA" in str(e) or "password" in str(e).lower():
                print("Введите пароль 2FA:")
                pw = input().strip()
                await client.sign_in(password=pw)
            else:
                raise

    me = await client.get_me()
    print(f"OK: @{me.username or me.id}")
    await client.disconnect()

    session_file = Path(str(session_path) + ".session")
    print(f"Gotovo. Sessiya: {session_file}")
    print("Bot - Zagruzit akkaunt - imya test - otpravte fayl kak dokument")


if __name__ == "__main__":
    asyncio.run(main())
