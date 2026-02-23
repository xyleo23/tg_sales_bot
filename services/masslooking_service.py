"""
Сервис масслукинга: массовый просмотр сторис пользователей из аудитории.
"""
import asyncio
import random
from pathlib import Path

from telethon import TelegramClient
from telethon import functions
from telethon.tl.types import PeerUser
from telethon.errors import FloodWaitError
from aiogram import Bot

from core.db.session import async_session_maker
from core.db.models import AudienceMember
from core.db.repos import account_repo, audience_repo
from core.telegram.client_manager import get_client
from loguru import logger


async def run_masslooking_task(
    account_id: int,
    audience_id: int,
    bot: Bot,
    admin_telegram_id: int,
    owner_user_id: int,
    api_id: int,
    api_hash: str,
    sessions_dir: Path,
) -> None:
    """
    Запуск задачи масслукинга: просмотр сторис пользователей из аудитории.

    Args:
        account_id: ID аккаунта (сессии) для просмотра.
        audience_id: ID аудитории с пользователями.
        bot: Объект aiogram.Bot для отправки отчётов.
        admin_telegram_id: Telegram ID админа для уведомлений.
        owner_user_id: ID владельца (user.id в БД) аккаунта и аудитории.
        api_id: Telegram API ID.
        api_hash: Telegram API Hash.
        sessions_dir: Путь к папке с .session файлами.
    """
    count = 0
    client: TelegramClient | None = None

    try:
        async with async_session_maker() as session:
            account = await account_repo.get_by_id(session, account_id, owner_user_id)
            audience = await audience_repo.get_by_id(session, audience_id, owner_user_id)

            if not account or not audience:
                await bot.send_message(
                    admin_telegram_id,
                    "❌ Аккаунт или аудитория не найдены.",
                )
                return

            members = await audience_repo.get_members_chunk(
                session, audience_id, offset=0, limit=10000
            )

        if not members:
            await bot.send_message(
                admin_telegram_id,
                "⚠️ В аудитории нет участников для просмотра.",
            )
            return

        session_path = sessions_dir / account.session_filename
        client = get_client(session_path, api_id, api_hash)

        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            await bot.send_message(
                admin_telegram_id,
                "❌ Сессия аккаунта не авторизована.",
            )
            return

        for member in members:
            while True:
                try:
                    entity_identifier = member.username if member.username else PeerUser(member.telegram_id)
                    user_entity = await client.get_entity(entity_identifier)

                    has_stories = (
                        getattr(user_entity, "stories_max_id", None)
                        and not getattr(user_entity, "stories_unavailable", False)
                    )

                    if has_stories:
                        await client(
                            functions.stories.ReadStoriesRequest(
                                peer=user_entity,
                                max_id=user_entity.stories_max_id,
                            )
                        )
                        count += 1
                        await asyncio.sleep(random.uniform(2.5, 5.0))
                    break

                except FloodWaitError as e:
                    logger.warning(f"Masslooking FloodWait: sleep {e.seconds}s")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logger.warning(f"Masslooking skip member {member.telegram_id}: {e}")
                    break

    except Exception as e:
        logger.exception("Masslooking task failed")
        await bot.send_message(
            admin_telegram_id,
            f"❌ Ошибка масслукинга: {e}",
        )
        return
    finally:
        if client and client.is_connected():
            await client.disconnect()

    await bot.send_message(
        admin_telegram_id,
        f"✅ Масслукинг завершён. Просмотрено {count} сторис.",
    )
