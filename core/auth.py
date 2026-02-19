"""
Проверки доступа по ролям.
"""
from typing import Optional
from core.db.models import User, Subscription


def is_super_admin(user: User) -> bool:
    return user.role == "super_admin"


def is_admin(user: User) -> bool:
    return user.role in ("admin", "super_admin")


def is_tester(user: User) -> bool:
    return user.role == "tester"


def has_subscription_access(user: User, subscription: Optional[Subscription]) -> bool:
    """
    Доступ к платным функциям: активная подписка ИЛИ tester/admin/super_admin.
    """
    if user.role in ("super_admin", "admin", "tester"):
        return True
    if not subscription:
        return False
    from core.subscription import is_subscription_active
    return is_subscription_active(subscription)


def can_access_admin_panel(user: User) -> bool:
    return user.role in ("super_admin", "admin")


def can_access_finance(user: User) -> bool:
    """Доступ к финансовой части (подписки, оплата, продление)."""
    return user.role == "super_admin"


def can_change_roles(user: User) -> bool:
    """Может менять роли других пользователей."""
    return user.role == "super_admin"


def can_export_logs(user: User) -> bool:
    """Может выгружать логи (свои)."""
    return user.role in ("tester", "admin", "super_admin")
