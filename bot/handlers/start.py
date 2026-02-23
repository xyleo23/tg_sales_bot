"""Стартовый хендлер."""
from aiogram import F, Router
from aiogram.types import Message

start_router = Router(name="start")


@start_router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 TG Sales Bot — рассылка и поиск клиентов в Telegram.\n\n"
        "Команды для админов:\n"
        "/add_session — загрузить .session аккаунт\n"
        "/add_audience — загрузить CSV с аудиторией"
    )
