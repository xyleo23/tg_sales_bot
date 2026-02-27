"""Pyrogram-based парсер участников чата."""
import asyncio
import re
from pathlib import Path
from typing import Optional

from loguru import logger
from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    UserAlreadyParticipant,
    ChatAdminRequired,
    ChannelPrivate,
)

from core.db.models import Account, Proxy
from core.clients.checker import _build_proxy_dict


def _resolve_session_path(account: Account) -> Path:
    """Вернуть путь к .session файлу аккаунта (поддерживает оба формата)."""
    if account.session_file_path:
        return Path(account.session_file_path)
    if account.session_filename:
        from bot.config import SESSIONS_DIR
        return SESSIONS_DIR / account.session_filename
    raise ValueError(f"Аккаунт #{account.id}: не задан путь к файлу сессии")


async def parse_chat_members(
    account: Account,
    proxy: Optional[Proxy],
    chat_link: str,
) -> list[str]:
    """Собрать участников чата через Pyrogram-клиент.

    Параметры:
        account   — аккаунт с .session файлом
        proxy     — прокси (или None)
        chat_link — username, t.me-ссылка или ID чата

    Возвращает список строк:
        "@username"      — если у пользователя есть username
        "<telegram_id>"  — если username нет

    Боты и удалённые аккаунты не включаются в результат.
    Raises при критических ошибках (FloodWait, ChannelPrivate и т.д.).
    """
    from bot.config import TG_API_ID, TG_API_HASH

    session_path = _resolve_session_path(account)
    if not session_path.exists():
        raise FileNotFoundError(f"Файл сессии не найден: {session_path}")

    session_name = str(session_path.with_suffix(""))

    client_kwargs: dict = {
        "name": session_name,
        "api_id": TG_API_ID,
        "api_hash": TG_API_HASH,
        "no_updates": True,
    }

    proxy_dict = _build_proxy_dict(proxy) if proxy else None
    if proxy_dict:
        client_kwargs["proxy"] = proxy_dict

    client = Client(**client_kwargs)
    result: list[str] = []

    try:
        await client.start()

        # Вступаем в чат, если нужно; игнорируем ошибки для открытых чатов
        try:
            await client.join_chat(chat_link)
            await asyncio.sleep(1)
        except UserAlreadyParticipant:
            pass
        except Exception as join_exc:
            logger.debug(f"join_chat({chat_link}): {join_exc} — продолжаем без вступления")

        async for member in client.get_chat_members(chat_link):
            user = member.user
            if user is None:
                continue
            if user.is_bot or user.is_deleted:
                continue
            if user.username:
                result.append(f"@{user.username}")
            else:
                result.append(str(user.id))

    except FloodWait as exc:
        logger.warning(f"parse_chat_members FloodWait {exc.value}s для {chat_link}")
        raise
    except (ChannelPrivate, ChatAdminRequired) as exc:
        logger.warning(f"parse_chat_members: нет доступа к {chat_link} — {exc}")
        raise
    except Exception as exc:
        logger.error(f"parse_chat_members: неожиданная ошибка для {chat_link}: {exc}")
        raise
    finally:
        try:
            await client.stop()
        except Exception:
            pass

    logger.info(f"parse_chat_members: {len(result)} участников из '{chat_link}'")
    return result
