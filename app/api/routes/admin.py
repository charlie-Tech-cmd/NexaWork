from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin_access
from app.db.session import get_db
from app.models.user import User
from app.services.admin_service import get_admin_dashboard_overview


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
)


@router.get("/dashboard")
async def admin_dashboard(
    current_admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return get_admin_dashboard_overview(
        db,
        current_admin.organization_id,
    )
