"""Главное меню и кнопка «Назад»."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_keyboard(user=None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📖 Инструкции", callback_data="menu_instructions"),
        InlineKeyboardButton(text="👥 Сообщество", callback_data="menu_community"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡️ Подписка", callback_data="menu_subscription"),
        InlineKeyboardButton(text="🔢 Конвертация номеров", callback_data="menu_convert"),
    )
    builder.row(
        InlineKeyboardButton(text="📤 Загрузить аккаунт", callback_data="menu_upload_account"),
        InlineKeyboardButton(text="🛒 Купить аккаунт", callback_data="menu_buy_account"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Парсер по участникам", callback_data="menu_parser_members"),
        InlineKeyboardButton(text="💬 Парсер по сообщениям", callback_data="menu_parser_messages"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡️ Аккаунты", callback_data="menu_accounts"),
        InlineKeyboardButton(text="👥 Аудитория", callback_data="menu_audience"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Инвайтинг", callback_data="menu_inviting"),
        InlineKeyboardButton(text="👀 Масслукинг", callback_data="menu_masslooking"),
    )
    builder.row(
        InlineKeyboardButton(text="📞 Звонки", callback_data="menu_calls"),
        InlineKeyboardButton(text="✉️ Рассылка", callback_data="menu_mailing"),
    )
    builder.row(
        InlineKeyboardButton(text="🔥 Прогрев", callback_data="menu_warming"),
        InlineKeyboardButton(text="📝 Автопостинг", callback_data="menu_autoposting"),
    )
    if user:
        from core.auth import can_export_logs
        if can_export_logs(user):
            builder.row(
                InlineKeyboardButton(text="📋 Выгрузить логи", callback_data="menu_logs"),
            )
    return builder.as_markup()


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_back"))
    return builder.as_markup()
