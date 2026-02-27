"""Аккаунты: загрузка .session, список, удаление."""
import re
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from bot.keyboards import main_menu_keyboard
from bot.states import UploadAccountStates
from bot.config import SESSIONS_DIR, TG_API_ID, TG_API_HASH
from core.db.repos import account_repo, activity_log_repo
from core.telegram.client_manager import check_session_valid
from core.auth import has_subscription_access

router = Router(name="accounts")

NAME_PATTERN = re.compile(r"^[a-zA-Zа-яА-ЯёЁ0-9_\s]{1,15}$")


def _session_path(user_id: int, account_id: int) -> Path:
    return SESSIONS_DIR / f"{user_id}_{account_id}.session"


# ----- Список аккаунтов -----
@router.callback_query(F.data == "menu_accounts")
async def list_accounts(callback: CallbackQuery, user, subscription, session):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    accounts = await account_repo.list_by_user(session, user.id)
    if not accounts:
        text = (
            "⚡️ <b>Аккаунты</b>\n\n"
            "У вас пока нет загруженных аккаунтов.\n"
            "Нажмите «Загрузить аккаунт» в главном меню или отправьте /upload."
        )
        await callback.message.answer(text, parse_mode="HTML")
        return
    lines = [f"• <b>{a.name}</b> — {a.status} (id {a.id})" for a in accounts]
    text = "⚡️ <b>Аккаунты</b>\n\n" + "\n".join(lines) + "\n\nЗагрузить ещё: /upload\nУдалить: нажмите кнопку ниже"
    builder = InlineKeyboardBuilder()
    for a in accounts:
        builder.row(
            InlineKeyboardButton(text=f"🗑 Удалить «{a.name}»", callback_data=f"account_delete_{a.id}")
        )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("account_delete_"))
async def delete_account(callback: CallbackQuery, user, subscription, session):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    try:
        account_id = int(callback.data.replace("account_delete_", ""))
    except ValueError:
        return
    deleted = await account_repo.delete(session, account_id, user.id)
    if deleted:
        await callback.message.answer("✅ Аккаунт удалён.")
    else:
        await callback.message.answer("Аккаунт не найден.")


# ----- Загрузка: начало FSM -----
@router.callback_query(F.data == "menu_upload_account")
async def upload_start_callback(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    await state.set_state(UploadAccountStates.wait_name)
    await state.update_data(user_db_id=user.id)
    await callback.message.answer(
        "Введите <b>имя аккаунта</b> (латиница/цифры, до 15 символов).\n"
        "Например: <code>main</code> или <code>аккаунт1</code>\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(F.text == "/upload")
async def upload_start_message(message: Message, user, subscription, session, state: FSMContext):
    if not has_subscription_access(user, subscription):
        await message.answer("⚠️ Нужна активная подписка.")
        return
    await state.set_state(UploadAccountStates.wait_name)
    await state.update_data(user_db_id=user.id)
    await message.answer(
        "Введите <b>имя аккаунта</b> (латиница/цифры, до 15 символов).\n"
        "Например: <code>main</code> или <code>аккаунт1</code>\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(UploadAccountStates.wait_name, F.text)
async def upload_got_name(message: Message, state: FSMContext, user, session):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    name = message.text.strip()
    if not NAME_PATTERN.match(name) or len(name) > 15:
        await message.answer("Имя должно быть от 1 до 15 символов (буквы, цифры, пробел). Попробуйте снова.")
        return
    await state.update_data(account_name=name[:15])
    await state.set_state(UploadAccountStates.wait_session_file)
    await message.answer(
        "Отправьте <b>файл .session</b> (документом).\n"
        "Получить его можно через официальные инструменты Telethon или экспорт сессии.\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(UploadAccountStates.wait_session_file, F.document)
async def upload_got_file(
    message: Message, state: FSMContext, user, session
):
    if message.document.file_name and not message.document.file_name.endswith(".session"):
        await message.answer("Нужен именно файл с расширением .session. Отправьте правильный файл или /cancel")
        return
    data = await state.get_data()
    account_name = data.get("account_name", "account")
    user_db_id = data.get("user_db_id", user.id)

    # Создаём запись с временным именем файла, потом обновим после сохранения
    acc = await account_repo.create(session, user_db_id, account_name, f"pending_{user_db_id}.session")
    session_filename = f"{user_db_id}_{acc.id}.session"
    acc.session_filename = session_filename
    await session.commit()
    await session.refresh(acc)

    file_id = message.document.file_id
    bot = message.bot
    file = await bot.get_file(file_id)
    path = SESSIONS_DIR / session_filename
    await bot.download_file(file.file_path, path)

    # Проверка сессии
    if TG_API_ID and TG_API_HASH:
        ok, err = await check_session_valid(path, TG_API_ID, TG_API_HASH)
        if not ok:
            path.unlink(missing_ok=True)
            await account_repo.delete(session, acc.id, user_db_id)
            await state.clear()
            await message.answer(f"❌ Сессия не прошла проверку: {err}. Попробуйте другой файл.")
            return

    await activity_log_repo.add(session, user_db_id, "upload_account", f"name:{account_name}, id:{acc.id}")
    await state.clear()
    await message.answer(
        f"✅ Аккаунт <b>{account_name}</b> добавлен и проверен.\n"
        "Раздел «Аккаунты» — список всех аккаунтов.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.message(UploadAccountStates.wait_session_file)
@router.message(UploadAccountStates.wait_name)
async def upload_wrong_type(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    await message.answer("Отправьте, пожалуйста, файл .session (как документ) или /cancel.")
