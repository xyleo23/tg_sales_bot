"""Асинхронный чекер Pyrogram-аккаунтов."""
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from loguru import logger
from pyrogram import Client
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, UserDeactivatedBan

from core.db.models import Account, Proxy


def _build_proxy_dict(proxy: Proxy) -> Optional[dict]:
    """Построить dict proxy для Pyrogram из модели Proxy.

    Поддерживаемые форматы proxy_string:
      - socks5://user:pass@host:port  (URL-формат)
      - host:port                     (без авторизации)
      - host:port:user:pass           (с авторизацией)
    """
    if not proxy or not proxy.proxy_string:
        return None

    ps = proxy.proxy_string.strip()

    if "://" in ps:
        parsed = urlparse(ps)
        result: dict = {
            "scheme": parsed.scheme or proxy.type or "socks5",
            "hostname": parsed.hostname,
            "port": parsed.port or 1080,
        }
        if parsed.username:
            result["username"] = parsed.username
        if parsed.password:
            result["password"] = parsed.password
        return result

    parts = ps.split(":")
    if len(parts) >= 2:
        result = {
            "scheme": proxy.type or "socks5",
            "hostname": parts[0],
            "port": int(parts[1]),
        }
        if len(parts) >= 4:
            result["username"] = parts[2]
            result["password"] = parts[3]
        return result

    return None


async def check_account(account: Account, proxy: Optional[Proxy] = None) -> str:
    """Проверить аккаунт через Pyrogram.

    Returns:
        'active'                — аккаунт живой
        'banned'                — аккаунт заблокирован (UserDeactivated*)
        'auth_key_unregistered' — сессия недействительна / устарела
    """
    from bot.config import TG_API_ID, TG_API_HASH

    if not account.session_file_path:
        logger.warning(f"check_account [{account.id}]: session_file_path не задан")
        return "auth_key_unregistered"

    session_path = Path(account.session_file_path)
    if not session_path.exists():
        logger.warning(f"check_account [{account.id}]: файл не найден — {session_path}")
        return "auth_key_unregistered"

    # Pyrogram принимает путь без расширения .session
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

    try:
        await client.connect()
        await client.get_me()
        return "active"
    except (UserDeactivated, UserDeactivatedBan):
        return "banned"
    except AuthKeyUnregistered:
        return "auth_key_unregistered"
    except Exception as exc:
        logger.warning(f"check_account [{account.id}] неожиданная ошибка: {exc}")
        return "auth_key_unregistered"
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass
