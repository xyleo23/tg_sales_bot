from aiogram.fsm.state import State, StatesGroup


class UploadAccountStates(StatesGroup):
    wait_name = State()
    wait_session_file = State()


class ParserMembersStates(StatesGroup):
    wait_name = State()
    wait_chat = State()
    wait_limit = State()


class ParserMessagesStates(StatesGroup):
    wait_name = State()
    wait_chat = State()
    wait_keywords = State()


class MailingStates(StatesGroup):
    wait_audience_id = State()
    wait_account_ids = State()
    wait_message = State()


class InvitingStates(StatesGroup):
    wait_audience_id = State()
    wait_chat = State()
    wait_account_id = State()


class WarmingStates(StatesGroup):
    wait_account_ids = State()


class AdminStates(StatesGroup):
    wait_extend = State()
    wait_change_role = State()


from bot.states.masslooking import MasslookingState
