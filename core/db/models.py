"""Модели БД для TG Sales Bot."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


USER_ROLE_USER = "user"
USER_ROLE_TESTER = "tester"
USER_ROLE_ADMIN = "admin"
USER_ROLE_SUPER_ADMIN = "super_admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default=USER_ROLE_USER)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    accounts: Mapped[list["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audiences: Mapped[list["Audience"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan: Mapped[str] = mapped_column(String(64), default="trial")
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Старое поле (одиночная загрузка через Telethon)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    session_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Новые поля: Pyrogram/Telethon session+json пара
    session_file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    json_file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True, index=True)
    proxy_string: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    proxy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True, index=True)
    # active | banned | flood_wait
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="accounts")
    proxy: Mapped[Optional["Proxy"]] = relationship(back_populates="accounts")


class Proxy(Base):
    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proxy_string: Mapped[str] = mapped_column(String(512))
    type: Mapped[str] = mapped_column(String(16), default="socks5")
    status: Mapped[str] = mapped_column(String(16), default="active")

    accounts: Mapped[list["Account"]] = relationship(back_populates="proxy")


class Audience(Base):
    __tablename__ = "audiences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(64), default="manual")
    source_chat: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="audiences")
    members: Mapped[list["AudienceMember"]] = relationship(
        back_populates="audience", cascade="all, delete-orphan"
    )


class AudienceMember(Base):
    __tablename__ = "audience_members"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audience_id: Mapped[int] = mapped_column(
        ForeignKey("audiences.id", ondelete="CASCADE"), index=True
    )
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    audience: Mapped["Audience"] = relationship(back_populates="members")


class Mailing(Base):
    __tablename__ = "mailings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    audience_id: Mapped[int] = mapped_column(ForeignKey("audiences.id"), index=True)
    account_ids: Mapped[str] = mapped_column(Text)
    message_text: Mapped[str] = mapped_column(Text)
    ai_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    sent_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    failed_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(255))
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
