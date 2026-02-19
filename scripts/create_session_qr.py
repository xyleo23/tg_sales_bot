"""
Создание .session через QR-код (без кода в Telegram).
Запуск: py scripts/create_session_qr.py
1. Отсканируйте QR в терминале телефоном (Telegram → Настройки → Устройства → Подключить)
2. Или откройте ссылку tg://login на телефоне
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from bot.config import TG_API_ID, TG_API_HASH, SESSIONS_DIR


async def main():
    if not TG_API_ID or not TG_API_HASH:
        print("ОШИБКА: Задайте TG_API_ID и TG_API_HASH в .env")
        return

    name = "test"
    session_path = SESSIONS_DIR / name
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(str(session_path), TG_API_ID, TG_API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"OK: @{me.username or me.id}")
        await client.disconnect()
        print(f"Сессия: {session_path}.session")
        return

    print("QR-login: otskaniruyte QR-kod telefonom.")
    print("Telegram: Nastroyki - Ustrovstva - Podklyuchit ustrovstvo\n")

    qr = await client.qr_login()

    # Сохранить QR в файл и вывести ссылку (Windows cp1251 не поддерживает ASCII QR)
    qr_file = SESSIONS_DIR / "qr_login.png"
    try:
        import qrcode
        q = qrcode.QRCode(border=2)
        q.add_data(qr.url)
        q.make()
        img = q.make_image(fill_color="black", back_color="white")
        img.save(qr_file)
        print(f"QR sohranen: {qr_file.absolute()}")
        print("Otkroyte fayl, otskaniruyte telefonom (Telegram - Ustrovstva - Podklyuchit)")
    except Exception as e:
        print(f"QR file error: {e}")
    print("\nIli otkroyte ssylku na telefone:")
    print(qr.url[:80] + "...")

    try:
        await qr.wait(timeout=120)
    except SessionPasswordNeededError:
        print("\nPassword 2FA:")
        pw = input().strip()
        await client.sign_in(password=pw)

    me = await client.get_me()
    print(f"\nOK: @{me.username or me.id}")
    await client.disconnect()

    print(f"Gotovo. Sessiya: {session_path}.session")
    print("V bote: Zagruzit akkaunt - imya 'test' - otpravte fayl kak dokument")


if __name__ == "__main__":
    asyncio.run(main())
