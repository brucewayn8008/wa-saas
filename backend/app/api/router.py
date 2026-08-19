from fastapi import APIRouter

from app.api.endpoints import (
    billing,
    conversations,
    dashboard,
    leads,
    listening,
    media,
    messages,
    onboarding,
    settings,
    users,
    webhook,
    webhook_wacli,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(listening.router, prefix="/listening", tags=["listening"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhooks"])
api_router.include_router(webhook_wacli.router, prefix="/webhook", tags=["webhooks"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])