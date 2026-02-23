# Деплой на сервер

## 1. Клонирование и настройка

```bash
cd /opt  # или ваша папка
git clone https://github.com/xyleo23/tg_sales_bot.git
cd tg_sales_bot
```

## 2. Создать .env

```bash
cp .env.example .env
nano .env
```

Заполните в .env:
- BOT_TOKEN — от @BotFather
- TG_API_ID, TG_API_HASH — с my.telegram.org
- SUPER_ADMIN_IDS — ваш telegram_id
- YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY — для оплаты

## 3. Установка

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# или: venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

## 4. Запуск

```bash
python -m bot.main
```

## 5. Systemd (автозапуск)

Создайте `/etc/systemd/system/tg-sales-bot.service`:

```ini
[Unit]
Description=TG Sales Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tg_sales_bot
EnvironmentFile=/opt/tg_sales_bot/.env
ExecStart=/opt/tg_sales_bot/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable tg-sales-bot
systemctl start tg-sales-bot
```

## 6. Webhook ЮKassa (оплата)

Если домен настроен — в личном кабинете ЮKassa укажите:
`https://ваш-домен.com/yookassa/webhook`

Проксируйте nginx на порт 8080.
