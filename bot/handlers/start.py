"""/start и главное меню."""
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu_keyboard

router = Router(name="start")
logger = logging.getLogger(__name__)

MAIN_MENU_TEXT = """<b>Главное меню</b>

С помощью этого бота вы можете:
1. Собрать аудиторию из чатов
2. Добавить людей в свою группу
3. Рассылка в личку с ИИ

Для новых пользователей — пробный период.
Подписка: раздел «⚡️ Подписка»."""


@router.message(CommandStart())
async def cmd_start(message: Message, user=None):
    logger.info("cmd_start: user_id=%s", message.from_user.id if message.from_user else None)
    await message.answer(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(user),
    )
