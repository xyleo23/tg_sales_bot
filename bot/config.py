"""Конфиг из .env"""
import os
from pathlib import Path
from dotenv import load_dotenv

_env_dir = Path(__file__).resolve().parent.parent
load_dotenv(_env_dir / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
TG_API_ID = int(os.getenv("TG_API_ID", "0") or 0)

# Роли (telegram_id через запятую в .env):
# SUPER_ADMIN_IDS — полный доступ
# ADMIN_IDS — без финансов и критичных настроек
# TESTER_IDS — как user, но без оплаты, могут выгружать логи
SUPER_ADMIN_IDS = [int(x.strip()) for x in os.getenv("SUPER_ADMIN_IDS", "").split(",") if x.strip()]
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
TESTER_IDS = [int(x.strip()) for x in os.getenv("TESTER_IDS", "").split(",") if x.strip()]
TG_API_HASH = (os.getenv("TG_API_HASH") or "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "10"))
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "")  # запасная ссылка, если YooKassa не настроена

# ЮKassa (оплата подписки)
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
SUBSCRIPTION_PRICE = float(os.getenv("SUBSCRIPTION_PRICE", "299"))
SUBSCRIPTION_DAYS = int(os.getenv("SUBSCRIPTION_DAYS", "30"))
YOOKASSA_WEBHOOK_PORT = int(os.getenv("YOOKASSA_WEBHOOK_PORT", "0"))  # 8080 для webhook

# Логи
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "")  # например logs/bot.log

# Задержки (секунды)
MAILING_DELAY_MIN = int(os.getenv("MAILING_DELAY_MIN", "30"))
MAILING_DELAY_MAX = int(os.getenv("MAILING_DELAY_MAX", "90"))
MAILING_MAX_PER_ACCOUNT = int(os.getenv("MAILING_MAX_PER_ACCOUNT", "20"))
INVITE_DELAY_SEC = int(os.getenv("INVITE_DELAY_SEC", "5"))

# Папка для .session файлов пользователей
SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions" / "telegram"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
