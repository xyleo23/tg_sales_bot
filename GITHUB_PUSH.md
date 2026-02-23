# Публикация на GitHub и деплой

## 1. Создайте репозиторий на GitHub

1. Зайдите на https://github.com/new
2. Имя: `tg_sales_bot` (или другое)
3. Выберите Public
4. **Не** ставьте галочки "Add README", "Add .gitignore" — репозиторий должен быть пустым
5. Нажмите Create repository

## 2. Подключите remote и отправьте код

```powershell
cd c:\Users\Admin\.cursor\tg_sales_bot

git remote add origin https://github.com/xyleo23/tg_sales_bot.git
git branch -M main
git push -u origin main
```

При первом push может попросить логин и пароль. Для пароля используйте **Personal Access Token** (GitHub → Settings → Developer settings → Personal access tokens).

## 3. На сервере

```bash
git clone https://github.com/xyleo23/tg_sales_bot.git
cd tg_sales_bot
cp .env.example .env
nano .env   # заполните BOT_TOKEN, TG_API_ID, TG_API_HASH, SUPER_ADMIN_IDS
pip install -r requirements.txt
python -m bot.main
```

Подробнее — см. DEPLOY.md
