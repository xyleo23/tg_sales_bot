"""Стартовый хендлер."""
from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard

start_router = Router(name="start")

MAIN_MENU_TEXT = "👋 TG Sales Bot — главное меню"


@start_router.message(F.text == "/start")
async def cmd_start(message: Message, user=None) -> None:
    await message.answer(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(user),
    )
