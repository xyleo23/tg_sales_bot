"""
Прогрев аккаунта: лёгкая активность (диалоги, просмотр), чтобы снизить риск бана.
"""
import asyncio
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from loguru import logger

from core.telegram.client_manager import get_client


async def warm_account(
    session_path: Path,
    api_id: int,
    api_hash: str,
    dialogs_limit: int = 10,
) -> tuple[bool, str]:
    """
    «Прогреть» аккаунт: получить список диалогов (имитация активности).
    Возвращает (success, message).
    """
    client = get_client(session_path, api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "Сессия не авторизована"
        count = 0
        async for _ in client.iter_dialogs(limit=dialogs_limit):
            count += 1
        await client.disconnect()
        return True, f"Прогрев выполнен: проверено диалогов {count}"
    except FloodWaitError as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        return False, f"FloodWait: подождите {e.value} сек"
    except Exception as e:
        logger.exception("warm_account failed")
        try:
            await client.disconnect()
        except Exception:
            pass
        return False, str(e)
