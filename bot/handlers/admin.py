"""Админ-панель: super_admin (полная), admin (ограниченная)."""
import re
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from core.auth import can_access_admin_panel, can_access_finance, can_change_roles, is_super_admin
from core.db.repos import user_repo, subscription_repo
from bot.states import AdminStates

router = Router(name="admin")


@router.message(F.text == "/admin")
async def admin_panel(message: Message, user, session, state: FSMContext):
    if not can_access_admin_panel(user):
        return
    await state.clear()
    if is_super_admin(user):
        text = "🔐 <b>Панель супер-админа</b>\n\nДоступны все функции."
    else:
        text = "🔐 <b>Панель админа</b>\n\nДоступ ограничен (без финансов и смены ролей)."
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_list_users"),
    )
    if can_access_finance(user):
        builder.row(
            InlineKeyboardButton(text="💰 Продлить подписку", callback_data="admin_extend_sub"),
        )
    if can_change_roles(user):
        builder.row(
            InlineKeyboardButton(text="🔄 Изменить роль", callback_data="admin_change_role"),
        )
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin_list_users")
async def admin_list_users(callback: CallbackQuery, user, session):
    await callback.answer()
    if not can_access_admin_panel(user):
        return
    users = await user_repo.list_all(session, limit=50)
    lines = []
    for u in users:
        sub = await subscription_repo.get_by_user_id(session, u.id)
        sub_str = f"до {sub.expires_at.strftime('%Y-%m-%d')}" if sub else "—"
        lines.append(f"• id{u.id} @{u.username or '—'} {u.role} sub:{sub_str}")
    text = "👥 <b>Пользователи</b> (последние 50):\n\n" + "\n".join(lines[:30])
    if len(lines) > 30:
        text += f"\n\n... и ещё {len(lines) - 30}"
    await callback.message.answer(text)


@router.callback_query(F.data == "admin_extend_sub")
async def admin_extend_sub(callback: CallbackQuery, user, session, state: FSMContext):
    await callback.answer()
    if not can_access_finance(user):
        await callback.message.answer("⛔ Нет доступа.")
        return
    await state.set_state(AdminStates.wait_extend)
    await callback.message.answer(
        "Введите: <code>user_id days</code>\n"
        "Например: <code>5 30</code> — продлить пользователю id=5 на 30 дней.\n"
        "Отмена: /admin"
    )


@router.message(AdminStates.wait_extend, F.text)
async def admin_extend_apply(message: Message, user, session, state: FSMContext):
    if not can_access_finance(user):
        await state.clear()
        return
    m = re.match(r"^\s*(\d+)\s+(\d+)\s*$", message.text or "")
    if not m:
        await message.answer("Неверный формат. Введите: <code>user_id days</code>")
        return
    target_id, days = int(m.group(1)), int(m.group(2))
    if days < 1 or days > 365:
        await message.answer("Дней должно быть от 1 до 365.")
        return
    sub = await subscription_repo.extend_or_create(session, target_id, "admin_extend", days)
    await state.clear()
    await message.answer(f"✅ Подписка пользователя id={target_id} продлена до {sub.expires_at.strftime('%Y-%m-%d')}.")


@router.callback_query(F.data == "admin_change_role")
async def admin_change_role(callback: CallbackQuery, user, session, state: FSMContext):
    await callback.answer()
    if not can_change_roles(user):
        await callback.message.answer("⛔ Нет доступа.")
        return
    await state.set_state(AdminStates.wait_change_role)
    await callback.message.answer(
        "Введите: <code>user_id role</code>\n"
        "Роли: user, tester, admin\n"
        "Например: <code>5 tester</code>\n"
        "Отмена: /admin"
    )


@router.message(AdminStates.wait_change_role, F.text)
async def admin_change_role_apply(message: Message, user, session, state: FSMContext):
    if not can_change_roles(user):
        await state.clear()
        return
    m = re.match(r"^\s*(\d+)\s+(user|tester|admin)\s*$", (message.text or "").strip().lower())
    if not m:
        await message.answer("Неверный формат. Введите: <code>user_id role</code> (роли: user, tester, admin)")
        return
    target_id, role = int(m.group(1)), m.group(2)
    target_user = await user_repo.get_by_id(session, target_id)
    if target_user and target_user.role == "super_admin":
        await message.answer("⛔ Роль супер-админа задаётся только в .env (SUPER_ADMIN_IDS).")
        await state.clear()
        return
    updated = await user_repo.update_role(session, target_id, role)
    await state.clear()
    if updated:
        await message.answer(f"✅ Роль пользователя id={target_id} изменена на {role}.")
    else:
        await message.answer("Пользователь не найден.")
