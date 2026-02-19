"""
Фильтр: доступ к платным разделам (подписка или роль tester/admin/super_admin).
"""
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Any

from core.auth import has_subscription_access


class ActiveSubscriptionFilter(BaseFilter):
    """Пропускать если есть доступ: активная подписка или роль tester/admin/super_admin."""

    async def __call__(self, event: Message | CallbackQuery, data: dict[str, Any]) -> bool:
        user = data.get("user")
        sub = data.get("subscription")
        if not user:
            return False
        return has_subscription_access(user, sub)
