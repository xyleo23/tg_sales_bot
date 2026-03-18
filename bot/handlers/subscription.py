"""Раздел «Подписка»: дата окончания, оплата через нативные Telegram Invoices."""
from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    ContentType,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import PAYMENT_PROVIDER_TOKEN, SUBSCRIPTION_DAYS, SUBSCRIPTION_PRICE
from bot.keyboards import main_menu_keyboard
from core.db.repos import activity_log_repo, subscription_repo
from core.subscription import format_expires_at, is_subscription_active

router = Router(name="subscription")


def _subscription_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if PAYMENT_PROVIDER_TOKEN:
        builder.row(
            InlineKeyboardButton(
                text=f"⚡️ Оплатить {SUBSCRIPTION_PRICE:.0f} ₽",
                callback_data="pay_subscription",
            )
        )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    return builder.as_markup()


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

    await callback.message.answer(text, reply_markup=_subscription_keyboard())


@router.callback_query(F.data == "pay_subscription")
async def pay_subscription(callback: CallbackQuery, bot: Bot, user):
    await callback.answer()
    if not PAYMENT_PROVIDER_TOKEN:
        await callback.message.answer(
            "⚠️ Оплата временно недоступна. Обратитесь в поддержку."
        )
        return

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Подписка на бота",
        description=f"Доступ ко всем функциям бота на {SUBSCRIPTION_DAYS} дней",
        payload=f"sub_{SUBSCRIPTION_DAYS}_days",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка", amount=int(SUBSCRIPTION_PRICE * 100))],
        start_parameter="pay_sub",
    )


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment_handler(message: Message, session, user):
    payment = message.successful_payment
    payment_id = payment.provider_payment_charge_id or payment.invoice_payload

    sub = await subscription_repo.extend_or_create(
        session,
        user.id,
        "telegram_payment",
        days=SUBSCRIPTION_DAYS,
        payment_id=payment_id,
    )
    await activity_log_repo.add(
        session, user.id, "payment_success",
        f"days:{SUBSCRIPTION_DAYS}, payment_id:{payment_id}",
    )
    expires_str = format_expires_at(sub)
    await message.answer(
        f"✅ Оплата прошла! Подписка продлена на {SUBSCRIPTION_DAYS} дней.\n"
        f"Действует до: {expires_str}",
        reply_markup=main_menu_keyboard(user),
    )
