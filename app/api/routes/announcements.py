from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_organization,
    get_current_user,
    has_permission,
    require_permission,
)
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.channels import (
    AnnouncementCreate,
    AnnouncementPage,
    AnnouncementResponse,
)
from app.services.announcement_service import (
    create_announcement,
    list_announcements,
)


router = APIRouter(
    prefix="/api/v1/announcements",
    tags=["announcements"],
)


@router.get("", response_model=AnnouncementPage)
def get_announcements(
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, gt=0),
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    items, next_cursor = list_announcements(
        db,
        current_organization.id,
        limit,
        before_id,
    )
    return AnnouncementPage(
        items=items,
        can_publish=has_permission(db, current_user, "ANNOUNCEMENT_CREATE"),
        next_cursor=next_cursor,
    )


@router.post(
    "",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_announcement(
    payload: AnnouncementCreate,
    current_user: User = Depends(require_permission("ANNOUNCEMENT_CREATE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        announcement = create_announcement(
            db,
            current_organization.id,
            current_user.id,
            payload.title,
            payload.body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return AnnouncementResponse(
        id=announcement.id,
        title=announcement.title,
        body=announcement.body,
        created_by_user_id=announcement.created_by_user_id,
        author_name=current_user.full_name,
        created_at=announcement.created_at,
    )
