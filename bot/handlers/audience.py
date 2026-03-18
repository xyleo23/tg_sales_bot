"""Аудитории: список, создание из парсера, экспорт в CSV."""
import asyncio
import csv
import io
import re
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.keyboards import main_menu_keyboard
from bot.states import ParserMembersStates, ParserMessagesStates
from bot.config import SESSIONS_DIR, TG_API_ID, TG_API_HASH, DATA_DIR
from bot.utils import is_telethon_configured
from core.db.session import async_session_maker
from core.db.repos import audience_repo, account_repo, activity_log_repo
from core.db.models import Proxy
from core.telegram.client_manager import get_client
from core.telegram.parser import parse_by_messages, normalize_chat_input
from core.auth import has_subscription_access

router = Router(name="audience")


def _get_session_path(account) -> Path:
    if account.session_file_path:
        return Path(account.session_file_path)
    return SESSIONS_DIR / account.session_filename


# ----- Список аудиторий -----
@router.callback_query(F.data == "menu_audience")
async def list_audiences(callback: CallbackQuery, user, subscription, session):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    audiences = await audience_repo.list_by_user(session, user.id)
    if not audiences:
        text = (
            "👥 <b>Аудитория</b>\n\n"
            "У вас пока нет аудиторий.\n"
            "Создайте из парсера: «Парсер по участникам» или «Парсер по сообщениям»."
        )
        await callback.message.answer(text, parse_mode="HTML")
        return
    lines = []
    builder = InlineKeyboardBuilder()
    for a in audiences:
        cnt = await audience_repo.count_members(session, a.id)
        lines.append(f"• <b>{a.name}</b> — {cnt} контактов (id {a.id})")
        builder.row(
            InlineKeyboardButton(text=f"📥 Экспорт «{a.name}»", callback_data=f"audience_export_{a.id}")
        )
    text = "👥 <b>Аудитория</b>\n\n" + "\n".join(lines)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("audience_export_"))
async def export_audience(callback: CallbackQuery, user, subscription, session):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    try:
        audience_id = int(callback.data.replace("audience_export_", ""))
    except ValueError:
        return
    aud = await audience_repo.get_by_id(session, audience_id, user.id)
    if not aud:
        await callback.message.answer("Аудитория не найдена.")
        return
    members = []
    offset = 0
    while True:
        chunk = await audience_repo.get_members_chunk(session, audience_id, offset=offset, limit=5000)
        if not chunk:
            break
        for m in chunk:
            members.append((m.telegram_id, m.username or "", m.first_name or "", m.last_name or ""))
        offset += len(chunk)
    if not members:
        await callback.message.answer("В аудитории нет контактов.")
        return
    await activity_log_repo.add(session, user.id, "export_audience", f"aud:{aud.name}, id:{audience_id}, count:{len(members)}")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["telegram_id", "username", "first_name", "last_name"])
    writer.writerows(members)
    buf.seek(0)
    file = BufferedInputFile(buf.getvalue().encode("utf-8-sig"), filename=f"audience_{aud.name}.csv")
    await callback.message.answer_document(file, caption=f"Экспорт аудитории «{aud.name}»: {len(members)} контактов")


# ----- Парсер по участникам (Pyrogram) -----
@router.callback_query(F.data == "menu_parser_members")
async def parser_members_start(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    accounts = await account_repo.list_by_user(session, user.id)
    if not accounts or not any(a.status == "active" for a in accounts):
        await callback.message.answer("Сначала добавьте хотя бы один активный аккаунт (Загрузить аккаунт).")
        return
    await state.set_state(ParserMembersStates.wait_chat)
    await state.update_data(user_db_id=user.id, telegram_id=user.telegram_id)
    await callback.message.answer(
        "👥 <b>Парсер по участникам</b>\n\n"
        "Отправьте <b>ссылку на чат/канал</b> или @username.\n"
        "Например: @durov или https://t.me/durov\n\nОтмена: /cancel",
        parse_mode="HTML",
    )


@router.message(ParserMembersStates.wait_chat, F.text)
async def parser_members_chat(message: Message, state: FSMContext, user, session, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return

    chat = normalize_chat_input(message.text)
    if not chat:
        await message.answer("Укажите ссылку или @username чата.")
        return

    data = await state.get_data()
    user_db_id = data.get("user_db_id", user.id)
    telegram_id = data.get("telegram_id", user.telegram_id)
    await state.clear()

    await message.answer("⏳ Парсинг запущен. Это может занять несколько минут. Вы получите файл с результатом.")

    async def run_parser():
        txt_path: Path | None = None
        try:
            async with async_session_maker() as sess:
                accounts = await account_repo.list_by_user(sess, user_db_id)
                account = next((a for a in accounts if a.status == "active"), None)
                if not account:
                    await bot.send_message(telegram_id, "❌ Нет активного аккаунта для парсинга.")
                    return

                proxy: Proxy | None = None
                if account.proxy_id:
                    r = await sess.execute(select(Proxy).where(Proxy.id == account.proxy_id))
                    proxy = r.scalar_one_or_none()

            from core.clients.parser import parse_chat_members
            members = await parse_chat_members(account, proxy, chat)

            if not members:
                await bot.send_message(telegram_id, "⚠️ Участников не найдено (чат пуст или нет доступа).")
                return

            # Сохранить в TXT-файл
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            safe_slug = re.sub(r"[^\w]", "_", chat)[:30]
            txt_path = DATA_DIR / f"chat_members_{safe_slug}_{telegram_id}.txt"
            txt_path.write_text("\n".join(members), encoding="utf-8")

            # Отправить файл
            doc = FSInputFile(txt_path, filename=txt_path.name)
            await bot.send_document(
                telegram_id,
                doc,
                caption=f"✅ Парсинг завершен. Найдено: {len(members)} участников.",
            )

            # Логируем
            async with async_session_maker() as sess2:
                await activity_log_repo.add(
                    sess2, user_db_id,
                    "parser_members_pyrogram",
                    f"chat:{chat}, count:{len(members)}",
                )

        except Exception as exc:
            from html import escape
            try:
                await bot.send_message(telegram_id, f"❌ Ошибка парсинга: {escape(str(exc))}")
            except Exception:
                pass
        finally:
            if txt_path and txt_path.exists():
                txt_path.unlink(missing_ok=True)

    asyncio.create_task(run_parser())


# ----- Парсер по сообщениям -----
@router.callback_query(F.data == "menu_parser_messages")
async def parser_messages_start(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    await callback.answer()
    if not is_telethon_configured():
        await callback.message.answer("⚠️ TG_API_ID и TG_API_HASH не заданы в .env. Обратитесь к администратору.")
        return
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    accounts = await account_repo.list_by_user(session, user.id)
    if not accounts or not any(a.status == "active" for a in accounts):
        await callback.message.answer("Сначала добавьте хотя бы один активный аккаунт.")
        return
    await state.set_state(ParserMessagesStates.wait_name)
    await state.update_data(user_db_id=user.id)
    await callback.message.answer(
        "💬 <b>Парсер по сообщениям</b>\n\n"
        "Введите <b>название аудитории</b>.\nОтмена: /cancel",
        parse_mode="HTML",
    )


@router.message(ParserMessagesStates.wait_name, F.text)
async def parser_messages_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    await state.update_data(audience_name=message.text.strip()[:100] or "По сообщениям")
    await state.set_state(ParserMessagesStates.wait_chat)
    await message.answer(
        "Отправьте <b>ссылку на чат/канал</b> или @username.\nОтмена: /cancel",
        parse_mode="HTML",
    )


@router.message(ParserMessagesStates.wait_chat, F.text)
async def parser_messages_chat(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    chat = normalize_chat_input(message.text)
    if not chat:
        await message.answer("Укажите ссылку или @username.")
        return
    await state.update_data(chat=chat)
    await state.set_state(ParserMessagesStates.wait_keywords)
    await message.answer(
        "Введите <b>ключевые слова</b> через запятую (авторы сообщений с этими словами попадут в аудиторию).\nОтмена: /cancel",
        parse_mode="HTML",
    )


@router.message(ParserMessagesStates.wait_keywords, F.text)
async def parser_messages_keywords(message: Message, state: FSMContext, user, session, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    keywords = [k.strip() for k in message.text.split(",") if k.strip()][:20]
    if not keywords:
        await message.answer("Введите хотя бы одно ключевое слово.")
        return
    data = await state.get_data()
    audience_name = data.get("audience_name", "По сообщениям")
    chat = data.get("chat", "")
    user_db_id = data.get("user_db_id", user.id)
    await state.clear()

    await message.answer("⏳ Парсинг по сообщениям запущен. Ожидайте уведомление.")

    async def run_parser():
        from html import escape
        from loguru import logger
        try:
            async with async_session_maker() as sess:
                accounts = await account_repo.list_by_user(sess, user_db_id)
                account = next((a for a in accounts if a.status == "active"), None)
                if not account:
                    await bot.send_message(user.telegram_id, "❌ Нет активного аккаунта.")
                    return
                path = _get_session_path(account)
                client = get_client(path, TG_API_ID, TG_API_HASH)
                try:
                    members = await parse_by_messages(client, chat, keywords, limit_messages=5000)
                except Exception as e:
                    await bot.send_message(user.telegram_id, f"❌ Ошибка парсинга: {escape(str(e))}")
                    return
                aud = await audience_repo.create(sess, user_db_id, audience_name, "parser_messages", chat)
                added = await audience_repo.add_members(
                    sess, aud.id,
                    [(m[0], m[1], m[2], m[3]) for m in members],
                )
                await activity_log_repo.add(sess, user_db_id, "parser_messages", f"aud:{audience_name}, chat:{chat}, count:{added}")
                await bot.send_message(
                    user.telegram_id,
                    f"✅ Аудитория «{audience_name}» создана.\nСобрано контактов: {added}.",
                    reply_markup=main_menu_keyboard(),
                )
        except Exception as e:
            logger.exception("run_parser (messages) failed")
            try:
                await bot.send_message(user.telegram_id, f"❌ Ошибка: {escape(str(e))}")
            except Exception:
                pass

    asyncio.create_task(run_parser())


@router.message(F.text == "/cancel")
async def cancel_parser(message: Message, state: FSMContext):
    current = await state.get_state()
    if current and "parser" in current.lower():
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
