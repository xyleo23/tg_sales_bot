"""Рассылка: выбор аудитории, аккаунтов, текст сообщения, запуск."""
import asyncio
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards import main_menu_keyboard
from bot.states import MailingStates
from bot.config import (
    SESSIONS_DIR,
    TG_API_ID,
    TG_API_HASH,
    MAILING_DELAY_MIN,
    MAILING_DELAY_MAX,
    MAILING_MAX_PER_ACCOUNT,
)
from bot.utils import is_telethon_configured
from core.db.session import async_session_maker
from core.db.repos import audience_repo, account_repo, mailing_repo, activity_log_repo
from core.telegram.sender import run_mailing
from core.auth import has_subscription_access

router = Router(name="mailing")


def _get_session_path(account) -> Path:
    return SESSIONS_DIR / account.session_filename


# ----- Раздел «Рассылка»: выбор аудитории -----
@router.callback_query(F.data == "menu_mailing")
async def mailing_start(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    await callback.answer()
    if not is_telethon_configured():
        await callback.message.answer("⚠️ TG_API_ID и TG_API_HASH не заданы в .env. Обратитесь к администратору.")
        return
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    audiences = await audience_repo.list_by_user(session, user.id)
    if not audiences:
        await callback.message.answer(
            "Сначала создайте аудиторию (Парсер по участникам или по сообщениям)."
        )
        return
    accounts = await account_repo.list_by_user(session, user.id)
    active_accounts = [a for a in accounts if a.status == "active"]
    if not active_accounts:
        await callback.message.answer("Добавьте хотя бы один активный аккаунт.")
        return
    await state.update_data(
        mailing_user_id=user.id,
        mailing_telegram_id=user.telegram_id,
    )
    lines = [f"• id <b>{a.id}</b> — {a.name} ({await audience_repo.count_members(session, a.id)} контактов)" for a in audiences]
    await callback.message.answer(
        "✉️ <b>Рассылка</b>\n\n"
        "Введите <b>id аудитории</b> из списка:\n\n" +
        "\n".join(lines) + "\n\nОтмена: /cancel",
        parse_mode="HTML",
    )
    await state.set_state(MailingStates.wait_audience_id)


@router.message(MailingStates.wait_audience_id, F.text == "/cancel")
@router.message(MailingStates.wait_account_ids, F.text == "/cancel")
@router.message(MailingStates.wait_message, F.text == "/cancel")
async def mailing_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_keyboard())


@router.message(MailingStates.wait_audience_id, F.text, F.text.regexp(r"^\d+$").as_("audience_id_str"))
async def mailing_audience_id(message: Message, state: FSMContext, audience_id_str: str, user, subscription, session):
    audience_id = int(audience_id_str)
    aud = await audience_repo.get_by_id(session, audience_id, user.id)
    if not aud:
        await message.answer("Аудитория не найдена. Введите id из списка или /cancel")
        return
    await state.update_data(mailing_audience_id=audience_id, mailing_audience_name=aud.name)
    accounts = await account_repo.list_by_user(session, user.id)
    active = [a for a in accounts if a.status == "active"]
    lines = [f"• id <b>{a.id}</b> — {a.name}" for a in active]
    await message.answer(
        "Введите <b>id аккаунтов через запятую</b> для ротации (например: 1,2,3):\n\n" +
        "\n".join(lines) + "\n\nОтмена: /cancel",
        parse_mode="HTML",
    )
    await state.set_state(MailingStates.wait_account_ids)


@router.message(MailingStates.wait_account_ids, F.text)
async def mailing_account_ids(message: Message, state: FSMContext, user, session):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    try:
        ids = [int(x.strip()) for x in message.text.split(",") if x.strip()]
    except ValueError:
        await message.answer("Введите числа через запятую (например: 1,2) или /cancel")
        return
    accounts = await account_repo.list_by_user(session, user.id)
    valid = [i for i in ids if any(a.id == i and a.status == "active" for a in accounts)]
    if not valid:
        await message.answer("Ни один из указанных аккаунтов не найден или не активен. Попробуйте снова.")
        return
    await state.update_data(mailing_account_ids=valid)
    await message.answer(
        "Отправьте <b>текст сообщения</b>, который будет отправлен каждому из аудитории.\n"
        "Поддерживаются плейсхолдеры: {name}, {username} — подставятся из контакта.\n\nОтмена: /cancel",
        parse_mode="HTML",
    )
    await state.set_state(MailingStates.wait_message)


@router.message(MailingStates.wait_message, F.text)
async def mailing_message(message: Message, state: FSMContext, user, session):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    data = await state.get_data()
    audience_id = data["mailing_audience_id"]
    account_ids = data["mailing_account_ids"]
    text = message.text.strip()
    if not text:
        await message.answer("Введите непустой текст.")
        return
    user_telegram_id = data.get("mailing_telegram_id", user.telegram_id)
    await state.clear()
    m = await mailing_repo.create(session, user.id, audience_id, account_ids, text, ai_role=None)
    await activity_log_repo.add(session, user.id, "mailing_start", f"aud:{audience_id}, accs:{account_ids}")
    await message.answer(
        f"⏳ Рассылка запущена (id {m.id}). Вы получите уведомление по завершении."
    )
    asyncio.create_task(_run_mailing_task(
        mailing_id=m.id,
        user_db_id=user.id,
        user_telegram_id=user_telegram_id,
        audience_id=audience_id,
        account_ids=account_ids,
        message_text=text,
    ))


async def _run_mailing_task(
    mailing_id: int,
    user_db_id: int,
    user_telegram_id: int,
    audience_id: int,
    account_ids: list[int],
    message_text: str,
):
    from datetime import datetime, timezone
    from aiogram import Bot
    from bot.config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    try:
        async with async_session_maker() as sess:
            aud = await audience_repo.get_by_id(sess, audience_id, user_db_id)
            if not aud:
                await bot.send_message(user_telegram_id, "❌ Аудитория не найдена.")
                return
            accounts = [await account_repo.get_by_id(sess, aid, user_db_id) for aid in account_ids]
            accounts = [a for a in accounts if a and a.status == "active"]
            if not accounts:
                await bot.send_message(user_telegram_id, "❌ Нет активных аккаунтов.")
                return
            session_paths = [SESSIONS_DIR / a.session_filename for a in accounts]
            offset = 0
            recipients = []
            while True:
                chunk = await audience_repo.get_members_chunk(sess, audience_id, offset=offset, limit=1000)
                if not chunk:
                    break
                for m in chunk:
                    msg = message_text.replace("{name}", m.first_name or "").replace("{username}", m.username or "")
                    recipients.append((m.telegram_id, msg))
                offset += len(chunk)
            if not recipients:
                await mailing_repo.update_status(sess, mailing_id, user_db_id, "done", sent_count=0, failed_count=0, finished_at=datetime.now(timezone.utc))
                await bot.send_message(user_telegram_id, "Рассылка завершена: в аудитории 0 контактов.")
                return
            await mailing_repo.update_status(sess, mailing_id, user_db_id, "running", started_at=datetime.now(timezone.utc))
        sent, failed = await run_mailing(
            session_paths,
            TG_API_ID,
            TG_API_HASH,
            recipients,
            delay_min=MAILING_DELAY_MIN,
            delay_max=MAILING_DELAY_MAX,
            max_per_account=MAILING_MAX_PER_ACCOUNT,
        )
        async with async_session_maker() as sess:
            await mailing_repo.update_status(
                sess, mailing_id, user_db_id, "done",
                sent_count=sent, failed_count=failed,
                finished_at=datetime.now(timezone.utc),
            )
        await bot.send_message(
            user_telegram_id,
            f"✅ Рассылка завершена.\nОтправлено: {sent}, ошибок: {failed}.",
            reply_markup=main_menu_keyboard(),
        )
    finally:
        await bot.session.close()
