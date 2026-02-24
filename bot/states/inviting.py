"""FSM состояния для инвайтинга (приглашение в группу/канал)."""
from aiogram.fsm.state import State, StatesGroup


class InvitingStates(StatesGroup):
    wait_audience_id = State()
    wait_chat = State()
    wait_account_id = State()
