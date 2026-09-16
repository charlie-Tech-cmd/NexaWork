from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings


app = FastAPI(title=f"{settings.app_name} API")

app.include_router(health_router)