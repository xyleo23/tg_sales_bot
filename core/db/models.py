"""
Модели БД: User, Subscription, Account, Audience, AudienceMember, Mailing.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.db.base import Base

if TYPE_CHECKING:
    pass


# Роли: user (обычный), tester (без оплаты, может выгружать логи), admin, super_admin
USER_ROLE_USER = "user"
USER_ROLE_TESTER = "tester"
USER_ROLE_ADMIN = "admin"
USER_ROLE_SUPER_ADMIN = "super_admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=USER_ROLE_USER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="user", lazy="selectin")
    audiences: Mapped[list["Audience"]] = relationship("Audience", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} username={self.username}>"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="trial", nullable=False)  # trial, basic, pro
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="subscription")

    def __repr__(self) -> str:
        return f"<Subscription user_id={self.user_id} plan={self.plan} expires_at={self.expires_at}>"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(15), nullable=False)  # до 15 символов
    session_filename: Mapped[str] = mapped_column(String(255), nullable=False)  # например {user_id}_{id}.session
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)  # active, blocked, warming
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="accounts")

    def __repr__(self) -> str:
        return f"<Account id={self.id} user_id={self.user_id} name={self.name} status={self.status}>"


class Audience(Base):
    __tablename__ = "audiences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # parser_members, parser_messages, manual
    source_chat: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # username или ссылка
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="audiences")
    members: Mapped[list["AudienceMember"]] = relationship("AudienceMember", back_populates="audience", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Audience id={self.id} user_id={self.user_id} name={self.name} source={self.source}>"


class AudienceMember(Base):
    __tablename__ = "audience_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audience_id: Mapped[int] = mapped_column(ForeignKey("audiences.id", ondelete="CASCADE"), nullable=False, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    audience: Mapped["Audience"] = relationship("Audience", back_populates="members")

    def __repr__(self) -> str:
        return f"<AudienceMember audience_id={self.audience_id} telegram_id={self.telegram_id}>"


class Mailing(Base):
    __tablename__ = "mailings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    audience_id: Mapped[int] = mapped_column(ForeignKey("audiences.id", ondelete="CASCADE"), nullable=False)
    account_ids: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array [1,2,3]
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_role: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # системный промпт для автоответов
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)  # draft, running, done, paused
    sent_count: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ActivityLog(Base):
    """Лог действий пользователя для аудита и экспорта тестировщиками."""
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # parser_start, mailing_start, etc.
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
