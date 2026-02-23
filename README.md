# TG Sales Bot

Бот для рассылки и поиска клиентов в Telegram. Поддержка масслукинга, загрузки аккаунтов (Telethon-сессий) и создания аудиторий из CSV.

## Установка

```bash
cd tg_sales_bot
pip install -r requirements.txt
cp .env.example .env
# Отредактируйте .env: BOT_TOKEN, SUPER_ADMIN_IDS, TG_API_ID, TG_API_HASH
```

## Запуск

```bash
py -m bot.main
```

## Команды для супер-админов

- `/add_session` — загрузить .session файл аккаунта (Telethon). Бот проверяет сессию через `TelegramClient` и сохраняет в БД.
- `/add_audience` — загрузить CSV со списком пользователей. Формат: `username, phone, telegram_id` (одна строка — один пользователь).
- `/cancel` — отменить текущее действие (FSM).

## Конфигурация (.env)

| Переменная      | Описание                             |
|-----------------|--------------------------------------|
| BOT_TOKEN       | Токен бота от @BotFather             |
| SUPER_ADMIN_IDS | Telegram ID админов через запятую    |
| TG_API_ID       | API ID с https://my.telegram.org     |
| TG_API_HASH     | API Hash с https://my.telegram.org   |

## Структура

```
tg_sales_bot/
├── bot/
│   ├── handlers/
│   │   ├── admin.py   # /add_session, /add_audience
│   │   └── start.py
│   ├── states/
│   │   └── admin.py   # AdminState (FSM)
│   ├── config.py
│   └── main.py
├── core/
│   └── db/            # models, session
├── data/
│   └── sessions/      # .session файлы
└── scripts/
```
