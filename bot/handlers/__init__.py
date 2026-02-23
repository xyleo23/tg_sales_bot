from aiogram import Router
from bot.handlers.start import router as start_router
from bot.handlers.subscription import router as subscription_router
from bot.handlers.accounts import router as accounts_router
from bot.handlers.audience import router as audience_router
from bot.handlers.mailing import router as mailing_router
from bot.handlers.inviting import router as inviting_router
from bot.handlers.warming import router as warming_router
from bot.handlers.masslooking import router as masslooking_router
from bot.handlers.logs import router as logs_router
from bot.handlers.admin import router as admin_router
from bot.handlers.menu import router as menu_router


def setup_routers(dp) -> None:
    dp.include_router(start_router)
    dp.include_router(subscription_router)
    dp.include_router(admin_router)
    dp.include_router(logs_router)
    dp.include_router(accounts_router)
    dp.include_router(audience_router)
    dp.include_router(mailing_router)
    dp.include_router(inviting_router)
    dp.include_router(warming_router)
    dp.include_router(masslooking_router)
    dp.include_router(menu_router)
