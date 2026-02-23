from aiogram import Router

from .admin import admin_router
from .start import start_router

router = Router(name="main")
router.include_router(start_router)
router.include_router(admin_router)
