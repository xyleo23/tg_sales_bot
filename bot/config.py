"""Конфигурация бота из .env."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("FATAL: BOT_TOKEN not set in .env", file=sys.stderr)
    sys.exit(1)


def _parse_ids(env_key: str) -> list[int]:
    raw = os.getenv(env_key, "")
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


SUPER_ADMIN_IDS: list[int] = _parse_ids("SUPER_ADMIN_IDS")
ADMIN_IDS: list[int] = _parse_ids("ADMIN_IDS")
TESTER_IDS: list[int] = _parse_ids("TESTER_IDS")

TG_API_ID = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")

DATA_DIR = BASE_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
DOWNLOADS_DIR = BASE_DIR / "downloads" / "sessions"

TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))

PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")
SUBSCRIPTION_PRICE = float(os.getenv("SUBSCRIPTION_PRICE", "299"))
SUBSCRIPTION_DAYS = int(os.getenv("SUBSCRIPTION_DAYS", "30"))

MAILING_DELAY_MIN = int(os.getenv("MAILING_DELAY_MIN", "30"))
MAILING_DELAY_MAX = int(os.getenv("MAILING_DELAY_MAX", "90"))
MAILING_MAX_PER_ACCOUNT = int(os.getenv("MAILING_MAX_PER_ACCOUNT", "20"))
INVITE_DELAY_SEC = int(os.getenv("INVITE_DELAY_SEC", "3"))
