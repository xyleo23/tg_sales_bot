"""Аккаунты: загрузка .session, список, удаление, массовая загрузка через ZIP."""
import io
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from bot.keyboards import main_menu_keyboard
from bot.states import UploadAccountStates
from bot.config import SESSIONS_DIR, DOWNLOADS_DIR, TG_API_ID, TG_API_HASH
from core.db.repos import account_repo, activity_log_repo
from core.db.models import Proxy
from core.telegram.client_manager import check_session_valid
from core.auth import has_subscription_access

router = Router(name="accounts")

NAME_PATTERN = re.compile(r"^[a-zA-Zа-яА-ЯёЁ0-9_\s]{1,15}$")


def _session_path(user_id: int, account_id: int) -> Path:
    return SESSIONS_DIR / f"{user_id}_{account_id}.session"


# ----- Список аккаунтов -----
@router.callback_query(F.data == "menu_accounts")
async def list_accounts(callback: CallbackQuery, user, subscription, session):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    accounts = await account_repo.list_by_user(session, user.id)
    if not accounts:
        text = (
            "⚡️ <b>Аккаунты</b>\n\n"
            "У вас пока нет загруженных аккаунтов.\n"
            "Нажмите «Загрузить аккаунт» в главном меню или отправьте /upload."
        )
        await callback.message.answer(text, parse_mode="HTML")
        return
    lines = [f"• <b>{a.name}</b> — {a.status} (id {a.id})" for a in accounts]
    text = "⚡️ <b>Аккаунты</b>\n\n" + "\n".join(lines) + "\n\nЗагрузить ещё: /upload\nУдалить: нажмите кнопку ниже"
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔍 Проверить аккаунты", callback_data="accounts_check_all")
    )
    for a in accounts:
        builder.row(
            InlineKeyboardButton(text=f"🗑 Удалить «{a.name}»", callback_data=f"account_delete_{a.id}")
        )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("account_delete_"))
async def delete_account(callback: CallbackQuery, user, subscription, session):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    try:
        account_id = int(callback.data.replace("account_delete_", ""))
    except ValueError:
        return
    deleted = await account_repo.delete(session, account_id, user.id)
    if deleted:
        await callback.message.answer("✅ Аккаунт удалён.")
    else:
        await callback.message.answer("Аккаунт не найден.")


# ----- Загрузка: начало FSM -----
@router.callback_query(F.data == "menu_upload_account")
async def upload_start_callback(callback: CallbackQuery, user, subscription, session, state: FSMContext):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return
    await state.set_state(UploadAccountStates.wait_name)
    await state.update_data(user_db_id=user.id)
    await callback.message.answer(
        "Введите <b>имя аккаунта</b> (латиница/цифры, до 15 символов).\n"
        "Например: <code>main</code> или <code>аккаунт1</code>\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(F.text == "/upload")
async def upload_start_message(message: Message, user, subscription, session, state: FSMContext):
    if not has_subscription_access(user, subscription):
        await message.answer("⚠️ Нужна активная подписка.")
        return
    await state.set_state(UploadAccountStates.wait_name)
    await state.update_data(user_db_id=user.id)
    await message.answer(
        "Введите <b>имя аккаунта</b> (латиница/цифры, до 15 символов).\n"
        "Например: <code>main</code> или <code>аккаунт1</code>\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(UploadAccountStates.wait_name, F.text)
async def upload_got_name(message: Message, state: FSMContext, user, session):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    name = message.text.strip()
    if not NAME_PATTERN.match(name) or len(name) > 15:
        await message.answer("Имя должно быть от 1 до 15 символов (буквы, цифры, пробел). Попробуйте снова.")
        return
    await state.update_data(account_name=name[:15])
    await state.set_state(UploadAccountStates.wait_session_file)
    await message.answer(
        "Отправьте <b>файл .session</b> (документом).\n"
        "Получить его можно через официальные инструменты Telethon или экспорт сессии.\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(UploadAccountStates.wait_session_file, F.document)
async def upload_got_file(
    message: Message, state: FSMContext, user, session
):
    fname = message.document.file_name or ""
    if fname and not fname.endswith(".session"):
        await message.answer("Нужен именно файл с расширением .session. Отправьте правильный файл или /cancel")
        return
    data = await state.get_data()
    account_name = data.get("account_name", "account")
    user_db_id = data.get("user_db_id", user.id)

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    acc = await account_repo.create(session, user_db_id, account_name, f"pending_{user_db_id}.session")
    session_filename = f"{user_db_id}_{acc.id}.session"
    acc.session_filename = session_filename
    await session.commit()
    await session.refresh(acc)

    path = SESSIONS_DIR / session_filename
    try:
        bot = message.bot
        file = await bot.get_file(message.document.file_id)
        await bot.download_file(file.file_path, path)
    except Exception as e:
        await account_repo.delete(session, acc.id, user_db_id)
        await state.clear()
        await message.answer(f"❌ Ошибка загрузки файла: {e}")
        return

    if TG_API_ID and TG_API_HASH:
        ok, err = await check_session_valid(path, TG_API_ID, TG_API_HASH)
        if not ok:
            path.unlink(missing_ok=True)
            await account_repo.delete(session, acc.id, user_db_id)
            await state.clear()
            await message.answer(f"❌ Сессия не прошла проверку: {err}. Попробуйте другой файл.")
            return

    await activity_log_repo.add(session, user_db_id, "upload_account", f"name:{account_name}, id:{acc.id}")
    await state.clear()
    await message.answer(
        f"✅ Аккаунт <b>{account_name}</b> добавлен и проверен.\n"
        "Раздел «Аккаунты» — список всех аккаунтов.",
        reply_markup=main_menu_keyboard(user),
    )


@router.message(UploadAccountStates.wait_session_file)
@router.message(UploadAccountStates.wait_name)
async def upload_wrong_type(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    await message.answer("Отправьте, пожалуйста, файл .session (как документ) или /cancel.")


# ──────────────────────────────────────────────────────────
# Массовая загрузка аккаунтов через ZIP
# ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu_upload_accounts_zip")
async def upload_zip_start(callback: CallbackQuery, user, state: FSMContext):
    await callback.answer()
    await state.set_state(UploadAccountStates.wait_for_zip)
    await state.update_data(user_db_id=user.id)
    await callback.message.answer(
        "📦 <b>Массовая загрузка аккаунтов</b>\n\n"
        "Отправьте <b>ZIP-архив</b>, внутри которого лежат файлы:\n"
        "  • <code>имя.session</code>\n"
        "  • <code>имя.json</code>  ← с тем же именем\n\n"
        "Каждая пара <code>имя.session</code> + <code>имя.json</code> — один аккаунт.\n"
        "Номер телефона читается из <code>.json</code> файла.\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(UploadAccountStates.wait_for_zip, F.document)
async def upload_zip_got_file(message: Message, state: FSMContext, user, session):
    doc = message.document

    # Проверяем mime-type и расширение
    is_zip = (
        (doc.mime_type in ("application/zip", "application/x-zip-compressed"))
        or (doc.file_name or "").lower().endswith(".zip")
    )
    if not is_zip:
        await message.answer(
            "❌ Нужен файл с расширением <b>.zip</b>.\n"
            "Упакуйте .session и .json файлы в ZIP-архив и отправьте ещё раз.\n\n"
            "Отмена: /cancel",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    user_db_id = data.get("user_db_id", user.id)

    status_msg = await message.answer("⏳ Скачиваю архив...")

    # Создаём временные папки
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    tmp_dir = Path(tempfile.mkdtemp(dir=DOWNLOADS_DIR, prefix=f"zip_{user_db_id}_"))
    zip_path = tmp_dir / (doc.file_name or "upload.zip")

    try:
        # Скачиваем ZIP
        bot = message.bot
        tg_file = await bot.get_file(doc.file_id)
        await bot.download_file(tg_file.file_path, zip_path)

        await status_msg.edit_text("📂 Распаковываю архив...")

        # Распаковываем
        extract_dir = tmp_dir / "extracted"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Собираем все .session файлы рекурсивно
        session_files = list(extract_dir.rglob("*.session"))
        if not session_files:
            await status_msg.edit_text(
                "❌ В архиве не найдено ни одного <code>.session</code> файла.\n"
                "Убедитесь, что файлы лежат в корне ZIP или в подпапках.",
                parse_mode="HTML",
            )
            return

        await status_msg.edit_text(f"🔍 Найдено .session файлов: {len(session_files)}. Обрабатываю...")

        added = 0
        skipped = 0
        errors: list[str] = []

        for sf in session_files:
            stem = sf.stem
            jf = sf.with_suffix(".json")

            if not jf.exists():
                errors.append(f"<code>{stem}</code> — нет .json файла")
                skipped += 1
                continue

            # Читаем телефон из JSON
            phone_number: str | None = None
            try:
                raw = jf.read_text(encoding="utf-8")
                payload = json.loads(raw)
                phone_number = (
                    payload.get("phone")
                    or payload.get("phone_number")
                    or payload.get("user", {}).get("phone")
                )
                if phone_number:
                    phone_number = str(phone_number).strip()
            except (json.JSONDecodeError, OSError) as exc:
                errors.append(f"<code>{stem}</code> — ошибка чтения JSON: {exc}")
                skipped += 1
                continue

            # Проверяем дубликат по phone_number
            if phone_number:
                existing = await account_repo.get_by_phone_number(session, phone_number)
                if existing:
                    errors.append(f"<code>{stem}</code> — аккаунт с номером {phone_number} уже существует")
                    skipped += 1
                    continue

            # Копируем файлы в постоянное хранилище
            dest_session = SESSIONS_DIR / sf.name
            dest_json = SESSIONS_DIR / jf.name
            shutil.copy2(sf, dest_session)
            shutil.copy2(jf, dest_json)

            try:
                await account_repo.create_with_paths(
                    session,
                    user_id=user_db_id,
                    session_file_path=str(dest_session),
                    json_file_path=str(dest_json),
                    phone_number=phone_number,
                )
                added += 1
            except Exception as exc:
                # Откатываем скопированные файлы при ошибке БД
                dest_session.unlink(missing_ok=True)
                dest_json.unlink(missing_ok=True)
                errors.append(f"<code>{stem}</code> — ошибка БД: {exc}")
                skipped += 1

        await activity_log_repo.add(
            session,
            user_db_id,
            "upload_accounts_zip",
            f"added:{added}, skipped:{skipped}, file:{doc.file_name}",
        )

        # Формируем итоговый отчёт
        lines = [
            f"✅ <b>Загрузка завершена</b>\n",
            f"Добавлено: <b>{added}</b>",
            f"Пропущено: <b>{skipped}</b>",
        ]
        if errors:
            lines.append("\n⚠️ <b>Проблемы:</b>")
            lines.extend(f"  • {e}" for e in errors[:20])
            if len(errors) > 20:
                lines.append(f"  ...и ещё {len(errors) - 20} ошибок")

        await status_msg.edit_text("\n".join(lines), parse_mode="HTML")

    except zipfile.BadZipFile:
        await status_msg.edit_text(
            "❌ Файл повреждён или не является ZIP-архивом. Проверьте файл и попробуйте снова."
        )
    except Exception as exc:
        await status_msg.edit_text(f"❌ Непредвиденная ошибка: {exc}")
    finally:
        # Удаляем временную директорию в любом случае
        shutil.rmtree(tmp_dir, ignore_errors=True)
        await state.clear()


@router.message(UploadAccountStates.wait_for_zip)
async def upload_zip_wrong_type(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_keyboard())
        return
    await message.answer(
        "Ожидаю <b>ZIP-архив</b> (отправьте файлом, не сжатым).\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────
# Проверка аккаунтов через Pyrogram
# ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "accounts_check_all")
async def check_all_accounts(callback: CallbackQuery, user, subscription, session):
    await callback.answer()
    if not has_subscription_access(user, subscription):
        await callback.message.answer("⚠️ Нужна активная подписка.")
        return

    accounts = await account_repo.list_by_user(session, user.id)
    if not accounts:
        await callback.message.answer("У вас нет аккаунтов для проверки.")
        return

    total = len(accounts)
    status_msg = await callback.message.answer(f"⏳ Проверяю {total} аккаунтов, подождите...")

    from core.clients.checker import check_account

    active_count = 0
    banned_count = 0
    auth_fail_count = 0

    for acc in accounts:
        proxy: Proxy | None = None
        if acc.proxy_id:
            result = await session.execute(select(Proxy).where(Proxy.id == acc.proxy_id))
            proxy = result.scalar_one_or_none()

        status = await check_account(acc, proxy)
        await account_repo.update_status(session, acc.id, user.id, status)

        if status == "active":
            active_count += 1
        elif status == "banned":
            banned_count += 1
        else:
            auth_fail_count += 1

    await activity_log_repo.add(
        session,
        user.id,
        "check_accounts",
        f"total:{total}, active:{active_count}, banned:{banned_count}, auth_fail:{auth_fail_count}",
    )

    report = (
        f"✅ <b>Проверка завершена</b>\n\n"
        f"Проверено: <b>{total}</b>\n"
        f"Живых: <b>{active_count}</b>\n"
        f"В бане: <b>{banned_count}</b>\n"
        f"Сессия недействительна: <b>{auth_fail_count}</b>"
    )
    await status_msg.edit_text(report, parse_mode="HTML")
