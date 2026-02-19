"""
Интеграция ЮKassa: создание платежа, webhook.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_payment(
    user_id: int,
    telegram_id: int,
    amount: float,
    days: int,
    return_url: str = "https://t.me/beliaev_sales_bot",  # куда вернуть после оплаты
) -> Optional[dict]:
    """
    Создать платёж в ЮKassa.
    Returns: {"payment_id": str, "confirmation_url": str} или None при ошибке.
    """
    try:
        from yookassa import Configuration, Payment
        from bot.config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
    except ImportError:
        logger.warning("yookassa не установлен: pip install yookassa")
        return None

    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        logger.warning("YOOKASSA_SHOP_ID или YOOKASSA_SECRET_KEY не заданы")
        return None

    Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)

    try:
        value = f"{amount:.2f}"
        payment = Payment.create({
            "amount": {"value": value, "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "capture": True,
            "description": f"Подписка на {days} дней",
            "metadata": {
                "user_id": str(user_id),
                "telegram_id": str(telegram_id),
                "days": str(days),
            },
        })
        conf = payment.confirmation
        url = getattr(conf, "confirmation_url", None) or (conf.get("confirmation_url") if isinstance(conf, dict) else "")
        return {
            "payment_id": payment.id,
            "confirmation_url": url or "",
        }
    except Exception as e:
        logger.exception("Ошибка создания платежа ЮKassa: %s", e)
        return None
