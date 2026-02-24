"""Сборка единого роутера из всех хендлеров."""
from aiogram import Router

from bot.handlers.start import start_router
from bot.handlers.subscription import router as subscription_router
from bot.handlers.menu import router as menu_router
from bot.handlers.accounts import router as accounts_router
from bot.handlers.audience import router as audience_router
from bot.handlers.mailing import router as mailing_router
from bot.handlers.inviting import router as inviting_router
from bot.handlers.warming import router as warming_router
from bot.handlers.masslooking import router as masslooking_router
from bot.handlers.logs import router as logs_router
from bot.handlers.admin import admin_router

router = Router(name="root")
router.include_router(start_router, name="start")
router.include_router(subscription_router, name="subscription")
router.include_router(accounts_router, name="accounts")
router.include_router(audience_router, name="audience")
router.include_router(mailing_router, name="mailing")
router.include_router(inviting_router, name="inviting")
router.include_router(warming_router, name="warming")
router.include_router(masslooking_router, name="masslooking")
router.include_router(logs_router, name="logs")
router.include_router(admin_router, name="admin")
router.include_router(menu_router, name="menu")

__all__ = ["router"]
