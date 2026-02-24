"""FSM состояния для прогрева аккаунтов."""
from aiogram.fsm.state import State, StatesGroup


class WarmingStates(StatesGroup):
    wait_account_ids = State()
