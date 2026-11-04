from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.user import User
from app.schemas.channels import AnnouncementResponse


def list_announcements(
    db: Session,
    organization_id: int,
    limit: int = 50,
    before_id: int | None = None,
) -> tuple[list[AnnouncementResponse], int | None]:
    statement = (
        select(Announcement, User.full_name)
        .join(
            User,
            (User.id == Announcement.created_by_user_id)
            & (User.organization_id == Announcement.organization_id),
        )
        .where(
            Announcement.organization_id == organization_id,
        )
    )
    if before_id is not None:
        statement = statement.where(Announcement.id < before_id)
    rows = db.execute(
        statement.order_by(Announcement.id.desc()).limit(limit + 1)
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = rows[-1][0].id if has_more and rows else None
    return [
        AnnouncementResponse(
            id=announcement.id,
            title=announcement.title,
            body=announcement.body,
            created_by_user_id=announcement.created_by_user_id,
            author_name=author_name,
            created_at=announcement.created_at,
        )
        for announcement, author_name in rows
    ], next_cursor


def create_announcement(
    db: Session,
    organization_id: int,
    creator_user_id: int,
    title: str,
    body: str,
) -> Announcement:
    active_user = db.scalar(
        select(User.id).where(
            User.id == creator_user_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
            User.is_super_admin.is_(False),
        )
    )
    if active_user is None:
        raise ValueError("User is unavailable in this organization")
    title = title.strip()
    body = body.strip()
    if not title or len(title) > 255:
        raise ValueError("Announcement title must contain 1 to 255 characters")
    if not body or len(body) > 10000:
        raise ValueError("Announcement body must contain 1 to 10000 characters")

    announcement = Announcement(
        organization_id=organization_id,
        created_by_user_id=creator_user_id,
        title=title,
        body=body,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement
