from fastapi import APIRouter
from app.api.v1.endpoints import tenants, chat, onboarding, admin ,health

router = APIRouter()

router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(health.router, tags=["health"])