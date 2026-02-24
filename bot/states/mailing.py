"""FSM состояния для рассылки."""
from aiogram.fsm.state import State, StatesGroup


class MailingStates(StatesGroup):
    wait_audience_id = State()
    wait_account_ids = State()
    wait_message = State()
