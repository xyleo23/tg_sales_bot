"""Прогрев аккаунтов: лёгкая активность для снижения риска бана."""
import asyncio
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards import main_menu_keyboard
from bot.states import WarmingStates
from bot.config import SESSIONS_DIR, TG_API_ID, TG_API_HASH
from bot.utils import is_telethon_configured
from core.db.session import async_session_maker
from core.db.repos import account_repo, activity_log_repo
from core.telegram.warming import warm_account
from core.auth import has_subscription_access

router = Router(name="warming")


def _session_path(account) -> Path:
    return SESSIONS_DIR / account.session_filename


@router.callback_query(F.data == "menu_warming")
async def warming_start(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    await callback.answer()
    if not is_telethon_configured():
        await callback.message.answer("⚠️ TG_API_ID и TG_API_HASH не заданы в .env. Обратитесь к администратору.")
        return
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    accounts = await account_repo.list_by_user(session, user.id)
    active = [a for a in accounts if a.status == "active"]
    if not active:
        await callback.message.answer("Нет активных аккаунтов для прогрева.")
        return
    await state.update_data(warming_user_telegram_id=user.telegram_id)
    await state.set_state(WarmingStates.wait_account_ids)
    lines = [f"• id <b>{a.id}</b> — {a.name}" for a in active]
    await callback.message.answer(
        "🔥 <b>Прогрев аккаунтов</b>\n\n"
        "Введите <b>id аккаунтов через запятую</b> (например: 1,2).\n"
        "Прогрев: проверка диалогов (имитация активности).\n\n" +
        "\n".join(lines) + "\n\nОтмена: /cancel",
        parse_mode="HTML",
    )


@router.message(WarmingStates.wait_account_ids, F.text)
async def warming_account_ids(message: Message, state: FSMContext, user, session, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    try:
        ids = [int(x.strip()) for x in message.text.split(",") if x.strip()]
    except ValueError:
        await message.answer("Введите числа через запятую (например: 1,2) или /cancel")
        return
    accounts = await account_repo.list_by_user(session, user.id)
    valid = [i for i in ids if any(a.id == i and a.status == "active" for a in accounts)]
    if not valid:
        await message.answer("Ни один аккаунт не найден или не активен.")
        return
    data = await state.get_data()
    user_telegram_id = data.get("warming_user_telegram_id", user.telegram_id)
    await state.clear()
    await message.answer("⏳ Прогрев запущен. Ожидайте уведомление.")

    async def run_warming():
        results = []
        async with async_session_maker() as sess:
            for aid in valid:
                acc = await account_repo.get_by_id(sess, aid, user.id)
                if not acc:
                    continue
                path = _session_path(acc)
                ok, msg = await warm_account(path, TG_API_ID, TG_API_HASH)
                results.append(f"• {acc.name}: {msg}")
            await activity_log_repo.add(sess, user.id, "warming", f"accs:{valid}, count:{len(results)}")
        text_result = "\n".join(results)
        await bot.send_message(
            user_telegram_id,
            f"🔥 <b>Прогрев завершён</b>\n\n{text_result}",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
        # Не закрывать bot.session — bot общий с диспетчером

    asyncio.create_task(run_warming())
