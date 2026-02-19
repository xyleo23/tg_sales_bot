"""Экспорт логов для тестировщиков и админов."""
import csv
import io
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from core.auth import can_export_logs
from core.db.repos import activity_log_repo

router = Router(name="logs")


@router.message(F.text == "/logs")
@router.callback_query(F.data == "menu_logs")
async def export_logs(event: Message | CallbackQuery, user, session):
    if not can_export_logs(user):
        if isinstance(event, CallbackQuery):
            await event.answer("⛔ Нет доступа.", show_alert=True)
        else:
            await event.answer("⛔ Нет доступа.")
        return
    if isinstance(event, CallbackQuery):
        await event.answer()
        msg = event.message
    else:
        msg = event
    logs = await activity_log_repo.get_by_user(session, user.id, limit=500)
    if not logs:
        await msg.answer("Нет записей логов.")
        return
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["created_at", "action", "details"])
    for log in reversed(logs):
        writer.writerow([
            log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
            log.action,
            (log.details or "")[:200],
        ])
    buf.seek(0)
    file = BufferedInputFile(buf.getvalue().encode("utf-8-sig"), filename="activity_log.csv")
    await msg.answer_document(file, caption=f"Лог действий ({len(logs)} записей)")
