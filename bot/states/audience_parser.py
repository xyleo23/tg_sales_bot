"""FSM состояния для парсеров аудитории (по участникам и по сообщениям)."""
from aiogram.fsm.state import State, StatesGroup


class ParserMembersStates(StatesGroup):
    wait_name = State()
    wait_chat = State()
    wait_limit = State()


class ParserMessagesStates(StatesGroup):
    wait_name = State()
    wait_chat = State()
    wait_keywords = State()
