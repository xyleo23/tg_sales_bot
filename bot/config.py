"""Конфигурация бота из .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Корень проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Super admin — только эти ID имеют доступ к /add_session и /add_audience
SUPER_ADMIN_IDS: list[int] = []
_raw = os.getenv("SUPER_ADMIN_IDS", "")
if _raw:
    SUPER_ADMIN_IDS = [int(x.strip()) for x in _raw.split(",") if x.strip().isdigit()]

# Telegram API (для Telethon)
TG_API_ID = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")

# Папка для .session файлов
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
