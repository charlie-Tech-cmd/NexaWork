from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.regions import router as regions_router
from app.core.config import settings


app = FastAPI(title=f"{settings.app_name} API")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(regions_router)