"""FSM состояния для админ-команд."""
from aiogram.fsm.state import State, StatesGroup


class AdminState(StatesGroup):
    waiting_for_session = State()
    waiting_for_csv = State()
