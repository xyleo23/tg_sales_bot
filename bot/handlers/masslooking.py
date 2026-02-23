"""Масслукинг: просмотр сторис пользователей из аудитории."""
import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from bot.keyboards import main_menu_keyboard
from bot.states import MasslookingState
from bot.config import SESSIONS_DIR, TG_API_ID, TG_API_HASH
from bot.utils import is_telethon_configured
from core.db.repos import audience_repo, account_repo
from core.auth import has_subscription_access
from services.masslooking_service import run_masslooking_task

router = Router(name="masslooking")


@router.callback_query(F.data == "menu_masslooking")
async def masslooking_start(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    """Начало масслукинга: показ списка аудиторий."""
    await callback.answer()
    if not is_telethon_configured():
        await callback.message.answer(
            "⚠️ TG_API_ID и TG_API_HASH не заданы в .env. Обратитесь к администратору."
        )
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

    builder = InlineKeyboardBuilder()
    for aud in audiences:
        cnt = await audience_repo.count_members(session, aud.id)
        builder.row(
            InlineKeyboardButton(
                text=f"{aud.name} ({cnt} контактов)",
                callback_data=f"masslook_aud_{aud.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_back"))

    await callback.message.answer(
        "👀 <b>Масслукинг</b>\n\nВыберите <b>аудиторию</b>, сторис участников которой просматривать:",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(MasslookingState.waiting_for_audience)


@router.callback_query(F.data.startswith("masslook_aud_"), MasslookingState.waiting_for_audience)
async def masslooking_audience_selected(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    """Выбрана аудитория → показ списка аккаунтов."""
    await callback.answer()
    try:
        audience_id = int(callback.data.replace("masslook_aud_", ""))
    except ValueError:
        return

    aud = await audience_repo.get_by_id(session, audience_id, user.id)
    if not aud:
        await callback.message.answer("Аудитория не найдена.")
        await state.clear()
        return

    await state.update_data(masslook_audience_id=audience_id, masslook_audience_name=aud.name)

    accounts = await account_repo.list_by_user(session, user.id)
    active = [a for a in accounts if a.status == "active"]
    if not active:
        await callback.message.answer("Нет активных аккаунтов. Добавьте аккаунт в разделе «Аккаунты».")
        await state.clear()
        return

    builder = InlineKeyboardBuilder()
    for acc in active:
        builder.row(
            InlineKeyboardButton(
                text=acc.name,
                callback_data=f"masslook_acc_{acc.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_masslooking"))

    await callback.message.answer(
        f"Выбрана аудитория <b>{aud.name}</b>.\n\nВыберите <b>аккаунт</b> для просмотра сторис:",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(MasslookingState.waiting_for_account)


@router.callback_query(F.data.startswith("masslook_acc_"), MasslookingState.waiting_for_account)
async def masslooking_account_selected(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    """Выбран аккаунт → подтверждение."""
    await callback.answer()
    try:
        account_id = int(callback.data.replace("masslook_acc_", ""))
    except ValueError:
        return

    account = await account_repo.get_by_id(session, account_id, user.id)
    if not account or account.status != "active":
        await callback.message.answer("Аккаунт не найден или не активен.")
        await state.clear()
        return

    data = await state.get_data()
    audience_id = data["masslook_audience_id"]
    audience_name = data["masslook_audience_name"]

    await state.update_data(masslook_account_id=account_id, masslook_account_name=account.name)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="▶️ Начать", callback_data="masslook_confirm"),
        InlineKeyboardButton(text="◀️ Отмена", callback_data="menu_back"),
    )

    await callback.message.answer(
        f"Запустить масслукинг для аудитории <b>{audience_name}</b> с аккаунта <b>{account.name}</b>?",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(MasslookingState.waiting_for_confirmation)


@router.callback_query(F.data == "masslook_confirm", MasslookingState.waiting_for_confirmation)
async def masslooking_confirm(callback: CallbackQuery, user, subscription, session, state: FSMContext, bot: Bot):
    """Подтверждение → запуск задачи в фоне."""
    await callback.answer()
    data = await state.get_data()
    audience_id = data["masslook_audience_id"]
    account_id = data["masslook_account_id"]

    await state.clear()
    await callback.message.answer("Процесс запущен в фоновом режиме.")

    asyncio.create_task(
        run_masslooking_task(
            account_id=account_id,
            audience_id=audience_id,
            bot=bot,
            admin_telegram_id=callback.from_user.id,
            owner_user_id=user.id,
            api_id=TG_API_ID,
            api_hash=TG_API_HASH,
            sessions_dir=SESSIONS_DIR,
        )
    )


@router.callback_query(F.data == "menu_back", StateFilter(MasslookingState))
async def masslooking_back(callback: CallbackQuery, state: FSMContext, user):
    """Кнопка «Назад» — выход из масслукинга в главное меню."""
    await callback.answer()
    await state.clear()
    from bot.handlers.start import MAIN_MENU_TEXT
    await callback.message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user))


@router.message(MasslookingState.waiting_for_audience, F.text == "/cancel")
@router.message(MasslookingState.waiting_for_account, F.text == "/cancel")
@router.message(MasslookingState.waiting_for_confirmation, F.text == "/cancel")
async def masslooking_cancel(message: Message, state: FSMContext, user):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_keyboard(user))
