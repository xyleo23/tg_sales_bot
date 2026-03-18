"""
Middleware: открывает сессию БД, получает/создаёт пользователя и выдаёт триал при первом заходе.
В data попадают: session (AsyncSession), user (User с подгруженной subscription).
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, TelegramObject, User as TgUser
from loguru import logger
from sqlalchemy import select

from bot.config import SUPER_ADMIN_IDS, TRIAL_DAYS
from core.db.models import Subscription
from core.db.repos import user_repo
from core.db.session import async_session_maker
from core.subscription import ensure_trial_for_new_user

BETA_MESSAGE = "Бот находится в закрытом бета-тестировании. Доступ только по приглашениям."


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

        async with async_session_maker() as session:
            try:
                user, _ = await user_repo.get_or_create(
                    session,
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                )
                await ensure_trial_for_new_user(session, user, TRIAL_DAYS)
                result = await session.execute(
                    select(Subscription).where(Subscription.user_id == user.id)
                )
                user_sub = result.scalar_one_or_none()

                if not user.is_allowed and telegram_user.id not in SUPER_ADMIN_IDS:
                    if isinstance(event, Message):
                        await event.answer(BETA_MESSAGE)
                    elif isinstance(event, CallbackQuery):
                        await event.answer(BETA_MESSAGE, show_alert=True)
                    elif isinstance(event, PreCheckoutQuery):
                        await event.answer(ok=False, error_message=BETA_MESSAGE)
                    return

                data["session"] = session
                data["user"] = user
                data["subscription"] = user_sub
                return await handler(event, data)
            except Exception:
                logger.exception("DbSessionMiddleware error")
                raise
