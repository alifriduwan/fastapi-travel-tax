from fastapi import APIRouter
from .user_router import router as user_router
from .province_router import router as province_router
from .authentication_router import router as authentication_router

router = APIRouter()
router.include_router(user_router)
router.include_router(province_router)
router.include_router(authentication_router)
