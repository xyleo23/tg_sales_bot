"""
Проверка подписки и выдача триала новым пользователям.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models import User, Subscription
from core.db.repos import subscription_repo


def is_subscription_active(sub: Optional[Subscription]) -> bool:
    """Подписка активна, если есть и expires_at > сейчас."""
    if not sub:
        return False
    now = datetime.now(timezone.utc)
    # если expires_at naive — сравниваем с utcnow()
    exp = sub.expires_at
    if exp.tzinfo is None:
        from datetime import timezone as tz
        exp = exp.replace(tzinfo=tz.utc)
    return exp > now


async def ensure_trial_for_new_user(session: AsyncSession, user: User, trial_days: int) -> Subscription:
    """Если у пользователя нет подписки — создать триал на trial_days дней."""
    sub = await subscription_repo.get_by_user_id(session, user.id)
    if sub:
        return sub
    return await subscription_repo.create_trial(session, user.id, trial_days)


def format_expires_at(sub: Subscription) -> str:
    """Форматировать дату окончания для отображения."""
    exp = sub.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp.strftime("%Y.%m.%d %H:%M:%S")
