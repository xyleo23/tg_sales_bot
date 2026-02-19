# Доведение до продакшена

Чек-лист перед выкладкой бота в прод.

## 1. Окружение

- [ ] `.env` не коммитить; секреты через переменные окружения или vault.
- [ ] `BOT_TOKEN` — продакшен-токен от @BotFather.
- [ ] `TG_API_ID` / `TG_API_HASH` — с my.telegram.org.
- [ ] `DATABASE_URL` — PostgreSQL: `postgresql+asyncpg://user:pass@host:5432/dbname` (или SQLite для малых нагрузок).
- [ ] `PAYMENT_LINK` — ссылка на оплату подписки (бот или сайт).
- [ ] `LOG_FILE` — путь к файлу логов (например `logs/bot.log`).

## 2. БД

- [ ] Запустить `py -m scripts.create_tables` против прод-БД.
- [ ] Регулярные бэкапы (PostgreSQL или копия `data/bot.db`).

## 3. Запуск

- [ ] **Polling:** `python -m bot.main` (подходит для VPS).
- [ ] **Webhook:** поднять HTTPS (nginx/caddy), проксировать запросы на приложение; в коде использовать aiogram webhook (см. документацию aiogram 3).
- [ ] Процесс под супервизором: systemd unit или supervisord, автоперезапуск при падении.

Пример systemd unit (`/etc/systemd/system/tg-sales-bot.service`):

```ini
[Unit]
Description=TG Sales Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/tg_sales_bot
EnvironmentFile=/opt/tg_sales_bot/.env
ExecStart=/opt/tg_sales_bot/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 4. Безопасность

- [ ] Папки `sessions/` и `data/` — права только для пользователя процесса бота.
- [ ] Не отдавать .session файлы наружу; не логировать BOT_TOKEN и API_HASH.
- [ ] **Роли:** задать `SUPER_ADMIN_IDS` в .env (telegram_id через запятую). Роль super_admin задаётся только через конфиг, не через панель.
- [ ] **Админы:** `ADMIN_IDS` — доступ к панели без финансов и смены ролей.
- [ ] **Тестировщики:** `TESTER_IDS` — доступ без оплаты, могут выгружать свои логи.

## 5. Мониторинг

- [ ] Логи: задать `LOG_FILE=logs/bot.log`, при необходимости ротация (loguru уже настроен).
- [ ] Оповещение при падении (healthcheck, алерт в Telegram/email).

## 6. Оплата (ЮKassa)

- [ ] В `.env`: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_WEBHOOK_PORT=8080`.
- [ ] В личном кабинете ЮKassa → Настройки → HTTP-уведомления: URL `https://ваш-домен/yookassa/webhook`.
- [ ] Порт 8080 должен быть доступен снаружи (nginx proxy на `/yookassa/webhook` → `localhost:8080`).

После выполнения этих пунктов бот готов к продакшену.
