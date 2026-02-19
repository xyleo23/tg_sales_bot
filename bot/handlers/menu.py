"""Обработка остальных кнопок главного меню (заглушки и платные разделы)."""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from core.auth import has_subscription_access

router = Router(name="menu")

# Платные действия: требуют активную подписку
PAID_ACTIONS = {
    "upload_account", "accounts", "parser_members", "parser_messages", "audience",
    "inviting", "masslooking", "calls", "mailing", "warming", "autoposting",
}


@router.callback_query(F.data.startswith("menu_"))
async def menu_callback(callback: CallbackQuery, user, subscription):
    action = (callback.data or "").replace("menu_", "")
    await callback.answer()

    if action == "back":
        from bot.handlers.start import MAIN_MENU_TEXT
        from bot.keyboards import main_menu_keyboard
        await callback.message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard(user))
        return

    if action == "subscription":
        # обрабатывается в subscription router
        return

    if action in PAID_ACTIONS and not has_subscription_access(user, subscription):
        await callback.message.answer(
            "⚠️ Для доступа к этому разделу нужна активная подписка.\n"
            "Перейдите в «⚡️ Подписка» для продления."
        )
        return

    # Заглушки (inviting, warming — свои роутеры)
    if action == "autoposting":
        await callback.message.answer("📝 Автопостинг — в разработке.")
    else:
        await callback.message.answer(f"Раздел «{action}» — в разработке.")
