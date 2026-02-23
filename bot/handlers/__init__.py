from aiogram import Router

from .admin import admin_router
from .menu import router as menu_router
from .start import start_router
from .subscription import router as subscription_router

router = Router(name="main")
router.include_router(start_router)
router.include_router(subscription_router)  # до menu — обрабатывает menu_subscription
router.include_router(menu_router)
router.include_router(admin_router)
