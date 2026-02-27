"""FSM состояния для загрузки аккаунта (.session)."""
from aiogram.fsm.state import State, StatesGroup


class UploadAccountStates(StatesGroup):
    wait_name = State()
    wait_session_file = State()
    wait_for_zip = State()
