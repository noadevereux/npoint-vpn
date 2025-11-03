from fastapi import APIRouter
from . import (
    admin,
    core,
    email_notifications,
    node,
    portal,
    subscription,
    system,
    user_template,
    user,
    home,
)

api_router = APIRouter()

routers = [
    admin.router,
    core.router,
    email_notifications.router,
    node.router,
    portal.api_router,
    portal.router,
    subscription.router,
    system.router,
    user_template.router,
    user.router,
    home.router,
]

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]