from fastapi import APIRouter

from backend.api.routes.auth import router as auth_router
from backend.api.routes.workspaces import router as workspaces_router
from backend.api.routes.calls import router as calls_router
from backend.api.routes.simulations import router as simulations_router
from backend.api.routes.templates import router as templates_router
from backend.api.routes.admin import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(calls_router)
api_router.include_router(simulations_router)
api_router.include_router(templates_router)
api_router.include_router(admin_router)
