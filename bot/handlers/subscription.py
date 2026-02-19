"""Раздел «Подписка»: дата окончания, кнопка активации, ЮKassa."""
import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import (
    PAYMENT_LINK,
    SUBSCRIPTION_PRICE,
    SUBSCRIPTION_DAYS,
)
from core.subscription import is_subscription_active, format_expires_at
from core.payment import create_payment

router = Router(name="subscription")


async def _get_payment_link(user) -> str | None:
    """Создать платёж в ЮKassa и вернуть ссылку. None — использовать PAYMENT_LINK."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: create_payment(
            user_id=user.id,
            telegram_id=user.telegram_id,
            amount=SUBSCRIPTION_PRICE,
            days=SUBSCRIPTION_DAYS,
        ),
    )
    if result:
        return result.get("confirmation_url")
    return None


@router.callback_query(F.data == "menu_subscription")
async def show_subscription(callback: CallbackQuery, user, subscription):
    await callback.answer()
    if not subscription:
        await callback.message.answer(
            "⚡️ Подписка\n\nПодписка не найдена. Обратитесь в поддержку."
        )
        return

    name = user.first_name or user.username or "Пользователь"
    expires_str = format_expires_at(subscription)
    active = is_subscription_active(subscription)
    status = "✅ Активна" if active else "❌ Истекла"
    reg_date = user.created_at.strftime("%Y.%m.%d %H:%M:%S") if user.created_at else "—"

    text = (
        "⚡️ <b>Подписка</b>\n\n"
        f"🦊 Имя: {name}\n"
        f"ID: <code>{user.telegram_id}</code>\n\n"
        f"Дата регистрации: {reg_date}\n"
        f"Подписка: до {expires_str}\n"
        f"Статус: {status}\n\n"
        f"Подписка на {SUBSCRIPTION_DAYS} дней — {SUBSCRIPTION_PRICE:.0f} ₽"
    )

    payment_url = await _get_payment_link(user)
    if not payment_url:
        payment_url = PAYMENT_LINK or "https://t.me/your_payment_bot"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"⚡️ Оплатить {SUBSCRIPTION_PRICE:.0f} ₽",
            url=payment_url,
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu_back")
    )
    await callback.message.answer(text, reply_markup=builder.as_markup())
