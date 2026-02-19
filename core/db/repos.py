"""
Репозитории: пользователь и подписка.
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timezone
from core.db.models import User, Subscription, Account, Audience, AudienceMember, Mailing, ActivityLog
from core.db.models import USER_ROLE_USER, USER_ROLE_TESTER, USER_ROLE_ADMIN, USER_ROLE_SUPER_ADMIN
from core.db.session import async_session_maker
from sqlalchemy import select, func


def _resolve_role(telegram_id: int) -> str:
    """Определить роль по telegram_id из конфига."""
    try:
        from bot.config import SUPER_ADMIN_IDS, ADMIN_IDS, TESTER_IDS
        if telegram_id in SUPER_ADMIN_IDS:
            return USER_ROLE_SUPER_ADMIN
        if telegram_id in ADMIN_IDS:
            return USER_ROLE_ADMIN
        if telegram_id in TESTER_IDS:
            return USER_ROLE_TESTER
    except Exception:
        pass
    return USER_ROLE_USER


class UserRepo:
    async def get_or_create(
        self,
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> tuple[User, bool]:
        """Вернуть пользователя по telegram_id или создать. Роль определяется по SUPER_ADMIN_IDS, ADMIN_IDS, TESTER_IDS."""
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        role = _resolve_role(telegram_id)
        if user:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.role = role
            await session.commit()
            await session.refresh(user)
            return user, False
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, True

    async def get_by_telegram_id(self, session: AsyncSession, telegram_id: int) -> Optional[User]:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, user_id: int) -> Optional[User]:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_role(self, session: AsyncSession, user_id: int, new_role: str) -> Optional[User]:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.role = new_role
        await session.commit()
        await session.refresh(user)
        return user

    async def list_all(self, session: AsyncSession, limit: int = 100) -> list[User]:
        result = await session.execute(select(User).order_by(User.created_at.desc()).limit(limit))
        return list(result.scalars().all())


class SubscriptionRepo:
    async def get_by_user_id(self, session: AsyncSession, user_id: int) -> Optional[Subscription]:
        result = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_trial(self, session: AsyncSession, user_id: int, days: int) -> Subscription:
        sub = await self.get_by_user_id(session, user_id)
        if sub:
            return sub
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        sub = Subscription(user_id=user_id, plan="trial", expires_at=expires_at)
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub

    async def extend_or_create(
        self,
        session: AsyncSession,
        user_id: int,
        plan: str,
        days: int,
        payment_id: Optional[str] = None,
    ) -> Subscription:
        sub = await self.get_by_user_id(session, user_id)
        now = datetime.now(timezone.utc)
        if sub:
            exp = sub.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            base = exp if exp > now else now
            sub.expires_at = base + timedelta(days=days)
            sub.plan = plan
            if payment_id:
                sub.payment_id = payment_id
        else:
            sub = Subscription(
                user_id=user_id,
                plan=plan,
                expires_at=now + timedelta(days=days),
                payment_id=payment_id,
            )
            session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub


class AccountRepo:
    async def create(self, session: AsyncSession, user_id: int, name: str, session_filename: str) -> Account:
        acc = Account(user_id=user_id, name=name.strip()[:15], session_filename=session_filename, status="active")
        session.add(acc)
        await session.commit()
        await session.refresh(acc)
        return acc

    async def list_by_user(self, session: AsyncSession, user_id: int) -> list[Account]:
        result = await session.execute(select(Account).where(Account.user_id == user_id).order_by(Account.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, account_id: int, user_id: int) -> Optional[Account]:
        result = await session.execute(
            select(Account).where(Account.id == account_id, Account.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, session: AsyncSession, account_id: int, user_id: int, status: str) -> Optional[Account]:
        acc = await self.get_by_id(session, account_id, user_id)
        if not acc:
            return None
        acc.status = status
        await session.commit()
        await session.refresh(acc)
        return acc

    async def delete(self, session: AsyncSession, account_id: int, user_id: int) -> bool:
        acc = await self.get_by_id(session, account_id, user_id)
        if not acc:
            return False
        from pathlib import Path
        from bot.config import SESSIONS_DIR
        path = Path(SESSIONS_DIR) / acc.session_filename
        if path.exists():
            path.unlink(missing_ok=True)
        await session.delete(acc)
        await session.commit()
        return True


class AudienceRepo:
    async def create(
        self,
        session: AsyncSession,
        user_id: int,
        name: str,
        source: str,
        source_chat: Optional[str] = None,
    ) -> Audience:
        aud = Audience(user_id=user_id, name=name.strip()[:100], source=source, source_chat=source_chat)
        session.add(aud)
        await session.commit()
        await session.refresh(aud)
        return aud

    async def list_by_user(self, session: AsyncSession, user_id: int) -> list[Audience]:
        result = await session.execute(
            select(Audience).where(Audience.user_id == user_id).order_by(Audience.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, audience_id: int, user_id: int) -> Optional[Audience]:
        result = await session.execute(
            select(Audience).where(Audience.id == audience_id, Audience.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_members(
        self,
        session: AsyncSession,
        audience_id: int,
        members: list[tuple[int, Optional[str], Optional[str], Optional[str]]],
    ) -> int:
        """members: list of (telegram_id, username, first_name, last_name). Возвращает количество добавленных."""
        added = 0
        for telegram_id, username, first_name, last_name in members:
            existing = await session.execute(
                select(AudienceMember).where(
                    AudienceMember.audience_id == audience_id,
                    AudienceMember.telegram_id == telegram_id,
                )
            )
            if existing.scalar_one_or_none():
                continue
            m = AudienceMember(
                audience_id=audience_id,
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(m)
            added += 1
        await session.commit()
        return added

    async def count_members(self, session: AsyncSession, audience_id: int) -> int:
        result = await session.execute(
            select(func.count(AudienceMember.id)).where(AudienceMember.audience_id == audience_id)
        )
        return result.scalar() or 0

    async def get_members_chunk(
        self, session: AsyncSession, audience_id: int, offset: int = 0, limit: int = 1000
    ) -> list[AudienceMember]:
        result = await session.execute(
            select(AudienceMember)
            .where(AudienceMember.audience_id == audience_id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


class MailingRepo:
    async def create(
        self,
        session: AsyncSession,
        user_id: int,
        audience_id: int,
        account_ids: list[int],
        message_text: str,
        ai_role: Optional[str] = None,
    ) -> Mailing:
        import json
        m = Mailing(
            user_id=user_id,
            audience_id=audience_id,
            account_ids=json.dumps(account_ids),
            message_text=message_text,
            ai_role=ai_role,
            status="draft",
        )
        session.add(m)
        await session.commit()
        await session.refresh(m)
        return m

    async def get_by_id(self, session: AsyncSession, mailing_id: int, user_id: int) -> Optional[Mailing]:
        result = await session.execute(
            select(Mailing).where(Mailing.id == mailing_id, Mailing.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, session: AsyncSession, user_id: int) -> list[Mailing]:
        result = await session.execute(
            select(Mailing).where(Mailing.user_id == user_id).order_by(Mailing.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        session: AsyncSession,
        mailing_id: int,
        user_id: int,
        status: str,
        sent_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        started_at=None,
        finished_at=None,
    ) -> Optional[Mailing]:
        m = await self.get_by_id(session, mailing_id, user_id)
        if not m:
            return None
        m.status = status
        if sent_count is not None:
            m.sent_count = sent_count
        if failed_count is not None:
            m.failed_count = failed_count
        if started_at is not None:
            m.started_at = started_at
        if finished_at is not None:
            m.finished_at = finished_at
        await session.commit()
        await session.refresh(m)
        return m


class ActivityLogRepo:
    async def add(self, session: AsyncSession, user_id: int, action: str, details: Optional[str] = None) -> None:
        log = ActivityLog(user_id=user_id, action=action, details=details)
        session.add(log)
        await session.commit()

    async def get_by_user(self, session: AsyncSession, user_id: int, limit: int = 1000) -> list[ActivityLog]:
        result = await session.execute(
            select(ActivityLog)
            .where(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


user_repo = UserRepo()
subscription_repo = SubscriptionRepo()
account_repo = AccountRepo()
audience_repo = AudienceRepo()
mailing_repo = MailingRepo()
activity_log_repo = ActivityLogRepo()
