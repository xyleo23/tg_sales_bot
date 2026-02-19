"""
Инвайтинг пользователей из аудитории в группу/канал через Telethon.
"""
import asyncio
from typing import List
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, ChannelPrivateError
from loguru import logger

# Лимиты Telegram: не более ~200 приглашений в день на канал, пачки по 50–100
INVITE_CHUNK_SIZE = 50
INVITE_DELAY_SEC = 5


async def invite_users_to_chat(
    client: TelegramClient,
    chat: str,
    user_ids: List[int],
    delay_sec: float = INVITE_DELAY_SEC,
    chunk_size: int = INVITE_CHUNK_SIZE,
) -> tuple[int, int]:
    """
    Пригласить пользователей (user_ids) в чат/канал.
    chat — username, ссылка или entity.
    Возвращает (invited_count, failed_count).
    """
    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return 0, len(user_ids)
        entity = await client.get_entity(chat)
        invited = 0
        failed = 0
        for i in range(0, len(user_ids), chunk_size):
            chunk = user_ids[i : i + chunk_size]
            input_users = []
            for uid in chunk:
                try:
                    user_entity = await client.get_entity(uid)
                    if hasattr(user_entity, "id"):
                        input_users.append(user_entity)
                except Exception:
                    failed += 1
            if not input_users:
                continue
            try:
                await client(InviteToChannelRequest(entity, input_users))
                invited += len(input_users)
            except UserPrivacyRestrictedError:
                failed += len(input_users)
            except FloodWaitError as e:
                logger.warning(f"Invite FloodWait {e.value}s")
                await asyncio.sleep(e.value)
                try:
                    await client(InviteToChannelRequest(entity, input_users))
                    invited += len(input_users)
                except Exception:
                    failed += len(input_users)
            except Exception as e:
                logger.warning(f"Invite chunk error: {e}")
                failed += len(input_users)
            await asyncio.sleep(delay_sec)
        await client.disconnect()
        return invited, failed
    except (ChannelPrivateError, ValueError) as e:
        logger.warning(f"invite_users_to_chat: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        raise
