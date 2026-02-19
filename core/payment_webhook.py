"""
Webhook для ЮKassa: при успешной оплате — продление подписки.
Запускается на отдельном порту (например 8080).
В личном кабинете ЮKassa укажите URL: https://ваш-домен/yookassa/webhook
"""
import logging
from aiohttp import web

logger = logging.getLogger(__name__) = logging.getLogger(__name__)


async def handle_yookassa_webhook(request: web.Request) -> web.Response:
    if request.method != "POST":
        return web.Response(status=405)
    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    event_type = body.get("event")  # payment.succeeded, payment.canceled, etc.
    if event_type != "payment.succeeded":
        return web.Response(status=200, text="OK")

    obj = body.get("object", {})
    payment_id = obj.get("id")
    status = obj.get("status")
    metadata = obj.get("metadata") or {}

    if status != "succeeded":
        return web.Response(status=200, text="OK")

    user_id_str = metadata.get("user_id")
    days_str = metadata.get("days", "30")
    if not user_id_str:
        logger.warning("Webhook ЮKassa: нет user_id в metadata, payment_id=%s", payment_id)
        return web.Response(status=200, text="OK")

    try:
        user_id = int(user_id_str)
        days = int(days_str)
    except (ValueError, TypeError):
        logger.warning("Webhook ЮKassa: некорректные metadata, payment_id=%s", payment_id)
        return web.Response(status=200, text="OK")

    try:
        from core.db.session import async_session_maker
        from core.db.repos import subscription_repo, user_repo
        from bot.config import BOT_TOKEN
        from aiogram import Bot

        async with async_session_maker() as session:
            await subscription_repo.extend_or_create(
                session, user_id, "yookassa", days, payment_id=payment_id
            )
            # Уведомление пользователю в Telegram
            user = await user_repo.get_by_id(session, user_id)
            if user and BOT_TOKEN:
                bot = Bot(token=BOT_TOKEN)
                try:
                    await bot.send_message(
                        user.telegram_id,
                        f"✅ Оплата прошла успешно!\nПодписка продлена на {days} дней.",
                    )
                except Exception as e:
                    logger.warning("Не удалось отправить уведомление: %s", e)
                finally:
                    await bot.session.close()
        logger.info("Подписка продлена: user_id=%s, days=%s, payment_id=%s", user_id, days, payment_id)
    except Exception as e:
        logger.exception("Ошибка продления подписки по webhook: %s", e)

    return web.Response(status=200, text="OK")


def create_webhook_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/yookassa/webhook", handle_yookassa_webhook)
    return app


def run_webhook_server(host: str = "0.0.0.0", port: int = 8080):
    """Запустить webhook-сервер (для использования в отдельном процессе или вместе с ботом)."""
    app = create_webhook_app()
    return app, host, port
