from fastapi import APIRouter
from .user_router import router as user_router

router = APIRouter()
router.include_router(user_router)
