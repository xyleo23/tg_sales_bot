"""Хендлеры меню: инструкции, сообщество, покупка аккаунта, заглушки."""
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.start import MAIN_MENU_TEXT
from bot.keyboards import main_menu_keyboard

router = Router()


def instructions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📗 Читать инструкции", url="https://t.me/")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )


def community_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🙋 Вступить в чат", url="https://t.me/")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )


def buy_account_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купить аккаунт", callback_data="shop_buy")],
            [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="shop_add_balance")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )


async def _safe_edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    """Edit message if possible, otherwise send a new one."""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=reply_markup)


@router.callback_query(F.data == "menu_instructions")
async def menu_instructions(callback: CallbackQuery) -> None:
    text = (
        "📚 <b>Инструкции по работе с ботом</b>\n\n"
        "Здесь собраны все обучающие материалы:\n"
        "-  Как покупать и загружать аккаунты\n"
        "-  Где брать прокси (IPv4, socks5)\n"
        "-  Настройка масслукинга и парсера\n\n"
        "<i>Перейдите в наш закрытый канал с инструкциями и видео-уроками:</i>"
    )
    await _safe_edit_or_answer(callback, text, reply_markup=instructions_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_community")
async def menu_community(callback: CallbackQuery) -> None:
    text = (
        "👥 <b>Наше закрытое комьюнити</b>\n\n"
        "В нашем чате мы:\n"
        "-  Делимся связками и кейсами\n"
        "-  Помогаем с настройкой бота\n"
        "-  Обсуждаем лимиты Telegram\n\n"
    )
    await _safe_edit_or_answer(callback, text, reply_markup=community_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_buy_account")
async def menu_buy_account(callback: CallbackQuery) -> None:
    text = (
        "💎 <b>Покупка аккаунта + прокси</b>\n\n"
        "Аккаунтов в наличии: 0\n"
        "Стоимость одного аккаунта: 500 рублей\n\n"
        "<i>При покупке аккаунта вы получаете сам аккаунт и прокси (IPv4, socks5).</i>"
    )
    await _safe_edit_or_answer(callback, text, reply_markup=buy_account_keyboard())
    await callback.answer()


@router.callback_query(F.data.in_({"back_to_main", "menu_back"}))
async def back_to_main_handler(callback: CallbackQuery, user=None) -> None:
    await callback.answer()
    await _safe_edit_or_answer(
        callback,
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(user),
    )


@router.callback_query(F.data == "menu_convert")
async def menu_convert(callback: CallbackQuery) -> None:
    await callback.answer("🔢 Конвертация номеров — в разработке", show_alert=True)


@router.callback_query(F.data == "menu_calls")
async def menu_calls(callback: CallbackQuery) -> None:
    await callback.answer("📞 Звонки — в разработке", show_alert=True)


@router.callback_query(F.data == "menu_autoposting")
async def menu_autoposting(callback: CallbackQuery) -> None:
    await callback.answer("📝 Автопостинг — в разработке", show_alert=True)


@router.callback_query(F.data == "shop_buy")
async def shop_buy(callback: CallbackQuery) -> None:
    await callback.answer("🛒 Магазин — в разработке", show_alert=True)


@router.callback_query(F.data == "shop_add_balance")
async def shop_add_balance(callback: CallbackQuery) -> None:
    await callback.answer("💰 Пополнение баланса — в разработке", show_alert=True)
