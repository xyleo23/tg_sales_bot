"""FSM состояния для управления прокси."""
from aiogram.fsm.state import State, StatesGroup


class ProxyStates(StatesGroup):
    wait_for_proxies = State()
