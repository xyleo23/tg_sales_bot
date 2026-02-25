"""Хендлеры меню: инструкции, сообщество, покупка аккаунта, заглушки магазина."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.handlers.start import MAIN_MENU_TEXT
from bot.keyboards import main_menu_keyboard

router = Router()

# --- Клавиатуры ---


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


# --- Инструкции ---


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
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=instructions_keyboard(),
    )
    await callback.answer()


# --- Сообщество ---


@router.callback_query(F.data == "menu_community")
async def menu_community(callback: CallbackQuery) -> None:
    text = (
        "👥 <b>Наше закрытое комьюнити</b>\n\n"
        "В нашем чате мы:\n"
        "-  Делимся связками и кейсами\n"
        "-  Помогаем с настройкой бота\n"
        "-  Обсуждаем лимиты Telegram\n\n"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=community_keyboard(),
    )
    await callback.answer()


# --- Купить аккаунт ---


@router.callback_query(F.data == "menu_buy_account")
async def menu_buy_account(callback: CallbackQuery) -> None:
    text = (
        "💎 <b>Покупка аккаунта + прокси</b>\n\n"
        "Аккаунтов в наличии: 0\n"
        "Стоимость одного аккаунта: 500 рублей\n\n"
        "<i>При покупке аккаунта вы получаете сам аккаунт и прокси (IPv4, socks5).</i>"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=buy_account_keyboard(),
    )
    await callback.answer()


# --- Назад в главное меню ---


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, user=None) -> None:
    """Возврат в главное меню по кнопке «⬅️ Назад»."""
    await callback.message.edit_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(user),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_back")
async def menu_back(callback: CallbackQuery) -> None:
    # Возврат в главное меню — текст и клавиатуру задаёт главный модуль (start/menu).
    # Здесь только закрываем уведомление; обработку menu_back можно вынести в общий роутер.
    await callback.answer()
    # Опционально: отредактировать сообщение обратно на главное меню (если знаем текст/клавиатуру).
    # await callback.message.edit_text(MAIN_MENU_TEXT, parse_mode="HTML", reply_markup=main_menu_keyboard())


# --- Заглушки магазина ---


@router.callback_query(F.data == "shop_buy")
async def shop_buy(callback: CallbackQuery) -> None:
    await callback.answer("В разработке", show_alert=True)


@router.callback_query(F.data == "shop_add_balance")
async def shop_add_balance(callback: CallbackQuery) -> None:
    await callback.answer("В разработке", show_alert=True)
