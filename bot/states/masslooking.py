"""Состояния FSM для масслукинга (просмотр сторис аудитории)."""
from aiogram.fsm.state import State, StatesGroup


class MasslookingState(StatesGroup):
    waiting_for_audience = State()
    waiting_for_account = State()
    waiting_for_confirmation = State()
