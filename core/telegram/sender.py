"""
Рассылка в личку через Telethon с ротацией аккаунтов.
Задержки между сообщениями для снижения риска бана.
"""
import asyncio
import random
from pathlib import Path
from typing import Optional
from telethon import TelegramClient
from telethon.errors import FloodWaitError, PeerFloodError, UserPrivacyRestrictedError
from loguru import logger

from core.telegram.client_manager import get_client


# Лимиты и задержки (можно вынести в config)
DELAY_MIN = 30
DELAY_MAX = 90
MAX_MESSAGES_PER_ACCOUNT = 20


async def send_to_user(
    client: TelegramClient,
    user_id: int,
    text: str,
) -> tuple[bool, Optional[str]]:
    """
    Отправить сообщение пользователю в личку.
    Возвращает (success, error_message).
    """
    try:
        await client.send_message(user_id, text)
        return True, None
    except UserPrivacyRestrictedError:
        return False, "privacy"
    except PeerFloodError:
        return False, "flood"
    except FloodWaitError as e:
        logger.warning(f"FloodWait {e.value}s")
        await asyncio.sleep(e.value)
        return await send_to_user(client, user_id, text)
    except Exception as e:
        logger.exception("send_to_user failed")
        return False, str(e)


async def run_mailing(
    session_paths: list[Path],
    api_id: int,
    api_hash: str,
    recipients: list[tuple[int, str]],  # (telegram_id, message_text)
    delay_min: int = DELAY_MIN,
    delay_max: int = DELAY_MAX,
    max_per_account: int = MAX_MESSAGES_PER_ACCOUNT,
) -> tuple[int, int]:
    """
    Рассылка по списку получателей с ротацией аккаунтов.
    Один клиент отправляет до max_per_account сообщений, затем переключение на следующий аккаунт.
    """
    if not session_paths:
        return 0, len(recipients)
    sent = 0
    failed = 0
    account_index = 0
    messages_from_current = 0
    client = None

    for telegram_id, text in recipients:
        need_new_client = client is None or messages_from_current >= max_per_account
        if need_new_client:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass
                client = None
            path = session_paths[account_index]
            client = get_client(path, api_id, api_hash)
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    await client.disconnect()
                    client = None
                    failed += 1
                    account_index = (account_index + 1) % len(session_paths)
                    continue
            except Exception:
                logger.exception("run_mailing connect failed")
                client = None
                failed += 1
                account_index = (account_index + 1) % len(session_paths)
                continue
            messages_from_current = 0
            account_index = (account_index + 1) % len(session_paths)

        if client:
            try:
                ok, _err = await send_to_user(client, telegram_id, text)
                if ok:
                    sent += 1
                    messages_from_current += 1
                else:
                    failed += 1
            except Exception:
                logger.exception("run_mailing send failed")
                failed += 1
        delay = random.randint(delay_min, delay_max)
        await asyncio.sleep(delay)

    if client:
        try:
            await client.disconnect()
        except Exception:
            pass
    return sent, failed
