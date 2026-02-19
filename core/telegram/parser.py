"""
Парсинг участников чата и авторов сообщений по ключевым словам.
"""
from typing import Optional
from telethon import TelegramClient
from telethon.tl.types import User as TgUser
from telethon.errors import ChannelPrivateError, ChatAdminRequiredError, FloodWaitError
from loguru import logger


async def parse_participants(
    client: TelegramClient,
    chat: str,
    limit: int = 10_000,
) -> list[tuple[int, Optional[str], Optional[str], Optional[str]]]:
    """
    Собрать участников чата/канала.
    chat — username, ссылка t.me/..., или ID.
    Возвращает список (telegram_id, username, first_name, last_name).
    """
    result = []
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return []
        entity = await client.get_entity(chat)
        async for user in client.iter_participants(entity, limit=limit):
            if not isinstance(user, TgUser) or user.bot or user.deleted:
                continue
            result.append((
                user.id,
                getattr(user, "username", None) or None,
                getattr(user, "first_name", None) or None,
                getattr(user, "last_name", None) or None,
            ))
        await client.disconnect()
    except FloodWaitError as e:
        logger.warning(f"FloodWait {e.value}s")
        await client.disconnect()
        raise
    except (ChannelPrivateError, ChatAdminRequiredError, ValueError) as e:
        logger.warning(f"parse_participants error: {e}")
        await client.disconnect()
        raise
    return result


async def parse_by_messages(
    client: TelegramClient,
    chat: str,
    keywords: list[str],
    limit_messages: int = 5000,
) -> list[tuple[int, Optional[str], Optional[str], Optional[str]]]:
    """
    Собрать авторов сообщений, содержащих ключевые слова.
    Возвращает список (telegram_id, username, first_name, last_name) без дубликатов.
    """
    seen: set[int] = set()
    result: list[tuple[int, Optional[str], Optional[str], Optional[str]]] = []
    keywords_lower = [k.lower().strip() for k in keywords if k.strip()]
    if not keywords_lower:
        return []

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return []
        entity = await client.get_entity(chat)
        count = 0
        async for msg in client.iter_messages(entity, limit=limit_messages):
            if count >= limit_messages:
                break
            if not msg.text:
                continue
            text_lower = msg.text.lower()
            if not any(kw in text_lower for kw in keywords_lower):
                continue
            count += 1
            sender = await msg.get_sender()
            if not sender or getattr(sender, "bot", False) or getattr(sender, "deleted", False):
                continue
            uid = getattr(sender, "id", None)
            if not uid or uid in seen:
                continue
            seen.add(uid)
            result.append((
                uid,
                getattr(sender, "username", None) or None,
                getattr(sender, "first_name", None) or None,
                getattr(sender, "last_name", None) or None,
            ))
        await client.disconnect()
    except FloodWaitError as e:
        logger.warning(f"FloodWait {e.value}s")
        await client.disconnect()
        raise
    except (ChannelPrivateError, ChatAdminRequiredError, ValueError) as e:
        logger.warning(f"parse_by_messages error: {e}")
        await client.disconnect()
        raise
    return result


def normalize_chat_input(text: str) -> str:
    """Извлечь username или ссылку из ввода пользователя."""
    text = text.strip()
    if text.startswith("https://t.me/"):
        part = text.split("t.me/")[-1].split("?")[0].rstrip("/")
        return part or text
    if text.startswith("@"):
        return text[1:]
    return text
