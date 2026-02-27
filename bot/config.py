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

ADMIN_IDS: list[int] = []
_raw = os.getenv("ADMIN_IDS", "")
if _raw:
    ADMIN_IDS = [int(x.strip()) for x in _raw.split(",") if x.strip().isdigit()]

TESTER_IDS: list[int] = []
_raw = os.getenv("TESTER_IDS", "")
if _raw:
    TESTER_IDS = [int(x.strip()) for x in _raw.split(",") if x.strip().isdigit()]

# Telegram API (для Telethon)
TG_API_ID = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")

# Папка для .session файлов
DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"

# Временная папка для распаковки ZIP-архивов (массовая загрузка)
DOWNLOADS_DIR = BASE_DIR / "downloads" / "sessions"

# Триал для новых пользователей (дней)
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))

# Оплата: нативные Telegram Invoices (Bot Payments API)
# Получить Provider Token: @BotFather → Payments → YooKassa (или другой провайдер)
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")
SUBSCRIPTION_PRICE = float(os.getenv("SUBSCRIPTION_PRICE", "299"))
SUBSCRIPTION_DAYS = int(os.getenv("SUBSCRIPTION_DAYS", "30"))

# Задержки (секунды) — для рассылки и инвайтинга
MAILING_DELAY_MIN = int(os.getenv("MAILING_DELAY_MIN", "1"))
MAILING_DELAY_MAX = int(os.getenv("MAILING_DELAY_MAX", "3"))
MAILING_MAX_PER_ACCOUNT = int(os.getenv("MAILING_MAX_PER_ACCOUNT", "20"))
INVITE_DELAY_SEC = int(os.getenv("INVITE_DELAY_SEC", "3"))
