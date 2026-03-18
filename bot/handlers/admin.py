"""Админ-хендлеры: загрузка сессий, аудиторий, управление доступом."""
import csv
from datetime import datetime
from io import StringIO
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Document, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, SessionPasswordNeededError

from bot.config import DATA_DIR, SESSIONS_DIR, SUPER_ADMIN_IDS, TG_API_HASH, TG_API_ID
from bot.states import AdminState
from core.db.models import Account, Audience, AudienceMember, User

admin_router = Router(name="admin")


@admin_router.message(F.text == "/add_session", F.from_user.id.in_(set(SUPER_ADMIN_IDS)))
async def cmd_add_session(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminState.waiting_for_session)
    await message.answer("Пришлите файл .session")


@admin_router.message(AdminState.waiting_for_session, F.document)
async def process_session_document(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession, user
) -> None:
    doc: Document = message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".session"):
        await message.answer("❌ Нужен файл с расширением .session")
        return

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{message.from_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.session"
    session_path = SESSIONS_DIR / safe_name

    try:
        await bot.download(doc.file_id, destination=session_path)
    except Exception as e:
        await message.answer(f"❌ Ошибка загрузки файла: {e}")
        return

    if not TG_API_ID or not TG_API_HASH:
        session_path.unlink(missing_ok=True)
        await state.clear()
        await message.answer(
            "❌ TG_API_ID и TG_API_HASH не заданы в .env. "
            "Получите их на https://my.telegram.org"
        )
        return

    client = TelegramClient(
        str(session_path.with_suffix("")),
        TG_API_ID,
        TG_API_HASH,
    )

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            session_path.unlink(missing_ok=True)
            for p in session_path.parent.glob(session_path.name + "*"):
                p.unlink(missing_ok=True)
            await state.clear()
            await message.answer(
                "❌ Сессия невалидна: требуется код авторизации. "
                "Используйте авторизованную сессию."
            )
            return

        me = await client.get_me()
        await client.disconnect()
    except (AuthKeyUnregisteredError, SessionPasswordNeededError) as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        session_path.unlink(missing_ok=True)
        for p in session_path.parent.glob(session_path.name + "*"):
            p.unlink(missing_ok=True)
        await state.clear()
        await message.answer(f"❌ Сессия невалидна: {e}")
        return
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        session_path.unlink(missing_ok=True)
        for p in session_path.parent.glob(session_path.name + "*"):
            p.unlink(missing_ok=True)
        await state.clear()
        await message.answer(f"❌ Ошибка проверки сессии: {e}")
        return

    account = Account(
        user_id=user.id,
        name=me.first_name or "",
        username=me.username or None,
        phone=me.phone or None,
        session_filename=safe_name,
    )
    session.add(account)
    await session.commit()

    await state.clear()
    username_display = f"@{me.username}" if me.username else (me.first_name or "без имени")
    await message.answer(
        f"✅ Аккаунт {username_display} успешно добавлен!"
    )


@admin_router.message(AdminState.waiting_for_session)
async def process_session_other(message: Message) -> None:
    await message.answer("Пришлите документ с расширением .session или /cancel для отмены.")


@admin_router.message(F.text == "/add_audience", F.from_user.id.in_(set(SUPER_ADMIN_IDS)))
async def cmd_add_audience(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminState.waiting_for_csv)
    await message.answer(
        "Пришлите CSV файл со списком пользователей.\n"
        "Формат: username, phone, telegram_id (одна строка — один юзер)"
    )


@admin_router.message(AdminState.waiting_for_csv, F.document)
async def process_csv_document(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession, user
) -> None:
    doc: Document = message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".csv"):
        await message.answer("❌ Нужен файл с расширением .csv")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / f"csv_{message.from_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"

    try:
        await bot.download(doc.file_id, destination=csv_path)
    except Exception as e:
        await message.answer(f"❌ Ошибка загрузки файла: {e}")
        return

    try:
        content = csv_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        csv_path.unlink(missing_ok=True)
        await message.answer(f"❌ Ошибка чтения файла: {e}")
        await state.clear()
        return

    csv_path.unlink(missing_ok=True)

    reader = csv.reader(StringIO(content))
    rows = list(reader)

    audience_name = Path(doc.file_name or "audience").stem or datetime.now().strftime("%Y-%m-%d_%H-%M")

    audience = Audience(user_id=user.id, name=audience_name, source="csv")
    session.add(audience)
    await session.flush()

    added = 0
    for row in rows:
        if not row:
            continue
        username = row[0].strip() if len(row) > 0 else None
        phone = row[1].strip() if len(row) > 1 else None
        try:
            telegram_id = int(row[2].strip()) if len(row) > 2 and row[2].strip() else None
        except (ValueError, TypeError):
            telegram_id = None

        if not username and not phone and not telegram_id:
            continue

        member = AudienceMember(
            audience_id=audience.id,
            username=username or None,
            phone=phone or None,
            telegram_id=telegram_id,
        )
        session.add(member)
        added += 1

    await session.commit()

    await state.clear()
    await message.answer(f"✅ Аудитория «{audience_name}» создана! Добавлено {added} пользователей.")


@admin_router.message(AdminState.waiting_for_csv)
async def process_csv_other(message: Message) -> None:
    await message.answer("Пришлите CSV файл или /cancel для отмены.")


@admin_router.message(F.text.startswith("/add_user"), F.from_user.id.in_(set(SUPER_ADMIN_IDS)))
async def cmd_add_user(message: Message, session: AsyncSession) -> None:
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /add_user &lt;telegram_id&gt;")
        return
    try:
        target_tg_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат ID. Ожидается число.")
        return

    result = await session.execute(select(User).where(User.telegram_id == target_tg_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        await message.answer(
            f"❌ Пользователь с Telegram ID {target_tg_id} не найден.\n"
            "Пользователь должен хотя бы раз написать боту."
        )
        return

    db_user.is_allowed = True
    await session.commit()
    name = db_user.first_name or db_user.username or str(target_tg_id)
    await message.answer(f"✅ Доступ выдан: {name} (ID: {target_tg_id})")


@admin_router.message(F.text.startswith("/del_user"), F.from_user.id.in_(set(SUPER_ADMIN_IDS)))
async def cmd_del_user(message: Message, session: AsyncSession) -> None:
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /del_user &lt;telegram_id&gt;")
        return
    try:
        target_tg_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат ID. Ожидается число.")
        return

    if target_tg_id in SUPER_ADMIN_IDS:
        await message.answer("❌ Нельзя отозвать доступ у супер-админа.")
        return

    result = await session.execute(select(User).where(User.telegram_id == target_tg_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        await message.answer(f"❌ Пользователь с Telegram ID {target_tg_id} не найден.")
        return

    db_user.is_allowed = False
    await session.commit()
    name = db_user.first_name or db_user.username or str(target_tg_id)
    await message.answer(f"✅ Доступ отозван: {name} (ID: {target_tg_id})")
