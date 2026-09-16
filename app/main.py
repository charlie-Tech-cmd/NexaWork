from fastapi import FastAPI

from app.core.config import settings


app = FastAPI(title=f"{settings.app_name} API")


@app.get("/")
async def root():
    return {"message": f"{settings.app_name} API is running"}