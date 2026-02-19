"""
Создание и получение Telethon-клиента по пути к .session файлу.
Используется для рассылки и парсинга от имени аккаунта пользователя.
"""
from pathlib import Path
from typing import Optional
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError
from loguru import logger


def get_client(
    session_path: Path,
    api_id: int,
    api_hash: str,
) -> TelegramClient:
    """
    Создать Telethon-клиент для сессии.
    session_path — полный путь к .session файлу (без расширения или с .session).
    """
    if not str(session_path).endswith(".session"):
        session_path = Path(str(session_path) + ".session")
    client = TelegramClient(
        str(session_path.with_suffix("")),
        api_id,
        api_hash,
    )
    return client


async def check_session_valid(session_path: Path, api_id: int, api_hash: str) -> tuple[bool, Optional[str]]:
    """
    Проверить, что сессия валидна (можно подключиться).
    Возвращает (success, error_message).
    """
    client = get_client(session_path, api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False, "Сессия не авторизована"
        me = await client.get_me()
        await client.disconnect()
        return True, None
    except AuthKeyUnregisteredError:
        return False, "Сессия устарела или отозвана"
    except Exception as e:
        logger.exception("check_session_valid failed")
        return False, str(e)
