"""
Middleware: открывает сессию БД, получает/создаёт пользователя и выдаёт триал при первом заходе.
В data попадают: session (AsyncSession), user (User с подгруженной subscription).
"""
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy import select

from core.db.session import async_session_maker
from core.db.models import User, Subscription
from core.db.repos import user_repo, subscription_repo
from core.subscription import ensure_trial_for_new_user
from bot.config import TRIAL_DAYS

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        telegram_user: TgUser | None = None
        if hasattr(event, "from_user") and event.from_user:
            telegram_user = event.from_user
        elif hasattr(event, "message") and event.message and event.message.from_user:
            telegram_user = event.message.from_user
        if not telegram_user:
            return await handler(event, data)

        try:
            async with async_session_maker() as session:
                user, _ = await user_repo.get_or_create(
                    session,
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                )
                await ensure_trial_for_new_user(session, user, TRIAL_DAYS)
                result = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
                user_sub = result.scalar_one_or_none()
                data["session"] = session
                data["user"] = user
                data["subscription"] = user_sub
                return await handler(event, data)
        except Exception as e:
            logger.exception("DbSessionMiddleware error: %s", e)
            data["session"] = None
            data["user"] = None
            data["subscription"] = None
            return await handler(event, data)
