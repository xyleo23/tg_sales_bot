"""Инвайтинг: приглашение аудитории в группу/канал."""
import asyncio
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards import main_menu_keyboard
from bot.states import InvitingStates
from bot.config import SESSIONS_DIR, TG_API_ID, TG_API_HASH, INVITE_DELAY_SEC
from bot.utils import is_telethon_configured
from core.db.session import async_session_maker
from core.db.repos import audience_repo, account_repo, activity_log_repo
from core.telegram.client_manager import get_client
from core.telegram.inviting import invite_users_to_chat
from core.telegram.parser import normalize_chat_input
from core.auth import has_subscription_access

router = Router(name="inviting")


def _session_path(account) -> Path:
    if account.session_file_path:
        return Path(account.session_file_path)
    return SESSIONS_DIR / account.session_filename


@router.callback_query(F.data == "menu_inviting")
async def inviting_start(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    await callback.answer()
    if not is_telethon_configured():
        await callback.message.answer("⚠️ TG_API_ID и TG_API_HASH не заданы в .env. Обратитесь к администратору.")
        return
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    audiences = await audience_repo.list_by_user(session, user.id)
    if not audiences:
        await callback.message.answer("Сначала создайте аудиторию (Парсер по участникам или по сообщениям).")
        return
    accounts = await account_repo.list_by_user(session, user.id)
    if not [a for a in accounts if a.status == "active"]:
        await callback.message.answer("Добавьте хотя бы один активный аккаунт.")
        return
    await state.update_data(inviting_user_id=user.id, inviting_telegram_id=user.telegram_id)
    lines = [f"• id <b>{a.id}</b> — {a.name} ({await audience_repo.count_members(session, a.id)} контактов)" for a in audiences]
    await callback.message.answer(
        "➕ <b>Инвайтинг</b>\n\n"
        "Введите <b>id аудитории</b>, участников которой пригласить в группу:\n\n" +
        "\n".join(lines) + "\n\nОтмена: /cancel",
        parse_mode="HTML",
    )
    await state.set_state(InvitingStates.wait_audience_id)


@router.message(InvitingStates.wait_audience_id, F.text)
async def inviting_audience_id(message: Message, state: FSMContext, user, session):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    try:
        audience_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите число (id аудитории) или /cancel")
        return
    aud = await audience_repo.get_by_id(session, audience_id, user.id)
    if not aud:
        await message.answer("Аудитория не найдена. Введите id из списка или /cancel")
        return
    await state.update_data(inviting_audience_id=audience_id)
    await state.set_state(InvitingStates.wait_chat)
    await message.answer(
        "Введите <b>ссылку на группу/канал</b> или @username, куда приглашать (нужны права на приглашение).\nОтмена: /cancel",
        parse_mode="HTML",
    )


@router.message(InvitingStates.wait_chat, F.text)
async def inviting_chat(message: Message, state: FSMContext, user, session):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    chat = normalize_chat_input(message.text)
    if not chat:
        await message.answer("Укажите ссылку или @username.")
        return
    await state.update_data(inviting_chat=chat)
    accounts = await account_repo.list_by_user(session, user.id)
    active = [a for a in accounts if a.status == "active"]
    lines = [f"• id <b>{a.id}</b> — {a.name}" for a in active]
    await state.set_state(InvitingStates.wait_account_id)
    await message.answer(
        "Введите <b>id аккаунта</b>, с которого приглашать:\n\n" +
        "\n".join(lines) + "\n\nОтмена: /cancel",
        parse_mode="HTML",
    )


@router.message(InvitingStates.wait_account_id, F.text)
async def inviting_account_id(message: Message, state: FSMContext, user, session, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    try:
        account_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите число (id аккаунта) или /cancel")
        return
    account = await account_repo.get_by_id(session, account_id, user.id)
    if not account or account.status != "active":
        await message.answer("Аккаунт не найден или не активен.")
        return
    data = await state.get_data()
    audience_id = data["inviting_audience_id"]
    chat = data["inviting_chat"]
    user_telegram_id = data.get("inviting_telegram_id", user.telegram_id)
    await state.clear()

    await message.answer("⏳ Инвайтинг запущен. Вы получите уведомление по завершении.")

    async def run_inviting(bot_instance: Bot):
        async with async_session_maker() as sess:
            aud = await audience_repo.get_by_id(sess, audience_id, user.id)
            if not aud:
                await bot_instance.send_message(user_telegram_id, "❌ Аудитория не найдена.")
                return
            user_ids = []
            offset = 0
            while True:
                chunk = await audience_repo.get_members_chunk(sess, audience_id, offset=offset, limit=500)
                if not chunk:
                    break
                user_ids.extend(m.telegram_id for m in chunk)
                offset += len(chunk)
            if not user_ids:
                await bot_instance.send_message(user_telegram_id, "В аудитории 0 контактов.")
                return
            await activity_log_repo.add(sess, user.id, "inviting_start", f"aud:{audience_id}, chat:{chat}, count:{len(user_ids)}")
        path = _session_path(account)
        client = get_client(path, TG_API_ID, TG_API_HASH)
        try:
            invited, failed = await invite_users_to_chat(client, chat, user_ids, delay_sec=INVITE_DELAY_SEC)
            await bot_instance.send_message(
                user_telegram_id,
                f"✅ Инвайтинг завершён.\nПриглашено: {invited}, ошибок: {failed}.",
                reply_markup=main_menu_keyboard(),
            )
        except Exception as e:
            await bot_instance.send_message(user_telegram_id, f"❌ Ошибка инвайтинга: {e}")
        # Не закрывать session — bot_instance это общий экземпляр бота

    asyncio.create_task(run_inviting(bot))


@router.message(InvitingStates.wait_audience_id, F.text == "/cancel")
@router.message(InvitingStates.wait_chat, F.text == "/cancel")
@router.message(InvitingStates.wait_account_id, F.text == "/cancel")
async def inviting_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_keyboard())
