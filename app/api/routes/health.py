from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.logging import request_logger


router = APIRouter()


@router.get("/health")
async def health_check():
    return {"message": "NexaWork API is running"}


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        request_logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NexaWork API is not ready",
        )

    return {"message": "NexaWork API is ready"}