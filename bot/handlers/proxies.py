"""Управление Proxy Pool: список и массовое добавление прокси."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from bot.states import ProxyStates
from core.db.models import Proxy

proxy_router = Router(name="proxies")


def _proxy_menu_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить прокси", callback_data="proxy_add"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    return builder


@proxy_router.callback_query(F.data == "menu_proxies")
async def list_proxies_callback(callback: CallbackQuery, session) -> None:
    await callback.answer()
    await _send_proxy_list(callback.message, session)


@proxy_router.message(F.text == "/proxies")
async def list_proxies_command(message: Message, session) -> None:
    await _send_proxy_list(message, session)


async def _send_proxy_list(target_message: Message, session) -> None:
    proxies = (await session.execute(select(Proxy).order_by(Proxy.id.desc()))).scalars().all()

    if not proxies:
        await target_message.answer(
            "🌐 <b>Proxy Pool</b>\n\n"
            "Список прокси пуст.\n"
            "Нажмите «Добавить прокси», чтобы загрузить прокси списком.",
            parse_mode="HTML",
            reply_markup=_proxy_menu_keyboard().as_markup(),
        )
        return

    lines = [f"• id {p.id} | {p.type} | {p.status} | <code>{p.proxy_string}</code>" for p in proxies]
    text = "🌐 <b>Proxy Pool</b>\n\n" + "\n".join(lines)
    await target_message.answer(text, parse_mode="HTML", reply_markup=_proxy_menu_keyboard().as_markup())


@proxy_router.callback_query(F.data == "proxy_add")
async def add_proxy_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(ProxyStates.wait_for_proxies)
    await callback.message.answer(
        "Отправьте прокси текстом, каждый с новой строки.\n"
        "Формат строки: <code>ip:port:login:password</code>\n\n"
        "Пример:\n"
        "<code>127.0.0.1:1080:user:pass</code>\n"
        "<code>127.0.0.2:1080:user:pass</code>\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@proxy_router.message(ProxyStates.wait_for_proxies, F.text)
async def add_proxy_parse(message: Message, state: FSMContext, session) -> None:
    if message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("Добавление прокси отменено.")
        return

    raw_lines = [line.strip() for line in message.text.splitlines() if line.strip()]
    if not raw_lines:
        await message.answer("Список пуст. Отправьте хотя бы одну строку с прокси или /cancel.")
        return

    invalid_lines: list[str] = []
    proxies_to_add: list[Proxy] = []

    existing_rows = (await session.execute(select(Proxy.proxy_string))).scalars().all()
    existing_proxy_strings = set(existing_rows)

    for line in raw_lines:
        parts = line.split(":")
        if len(parts) != 4 or not parts[1].isdigit():
            invalid_lines.append(line)
            continue
        if line in existing_proxy_strings:
            continue
        proxies_to_add.append(Proxy(proxy_string=line))
        existing_proxy_strings.add(line)

    if proxies_to_add:
        session.add_all(proxies_to_add)
        await session.commit()

    await state.clear()

    response = [
        "✅ Обработка прокси завершена.",
        f"Добавлено: {len(proxies_to_add)}",
        f"Некорректных строк: {len(invalid_lines)}",
    ]
    if invalid_lines:
        preview = "\n".join(f"• <code>{line}</code>" for line in invalid_lines[:10])
        response.append("\nНекорректные строки:\n" + preview)
    await message.answer("\n".join(response), parse_mode="HTML", reply_markup=_proxy_menu_keyboard().as_markup())


@proxy_router.message(ProxyStates.wait_for_proxies)
async def add_proxy_wrong_type(message: Message) -> None:
    await message.answer("Отправьте текст со списком прокси (каждый с новой строки) или /cancel.")
