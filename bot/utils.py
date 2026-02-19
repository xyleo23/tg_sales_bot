"""Вспомогательные функции для хендлеров."""
from bot.config import TG_API_ID, TG_API_HASH


def is_telethon_configured() -> bool:
    """Проверка, что TG_API_ID и TG_API_HASH заданы для работы с Telethon."""
    return bool(TG_API_ID and TG_API_HASH)
