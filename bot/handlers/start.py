"""Стартовый хендлер."""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard

start_router = Router(name="start")

MAIN_MENU_TEXT = "👋 <b>TG Sales Bot</b> — главное меню"


@start_router.message(CommandStart())
async def cmd_start(message: Message, user=None) -> None:
    await message.answer(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(user),
    )
