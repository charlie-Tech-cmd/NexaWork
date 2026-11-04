from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
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
    ChannelConversation,
    ChannelCreate,
    ChannelMemberAdd,
    ChannelMemberResponse,
    ChannelMemberRoleUpdate,
    ChannelPage,
    ChannelSummary,
)
from app.services.channel_service import (
    ChannelAccessError,
    ChannelValidationError,
    add_channel_member,
    channel_summary,
    create_channel,
    join_public_channel,
    list_channel_members,
    list_channels,
    remove_channel_member,
    update_channel_member_role,
)


router = APIRouter(prefix="/api/v1/channels", tags=["channels"])


def _channel_error(exc: ValueError) -> None:
    if isinstance(exc, ChannelAccessError):
        raise HTTPException(status_code=404, detail="Channel not found") from exc
    if isinstance(exc, ChannelValidationError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(
        status_code=500,
        detail="Internal channel error",
    ) from exc


def _conversation_response(
    db: Session,
    channel,
    user_id: int,
) -> ChannelConversation:
    summary = channel_summary(
        db,
        channel.organization_id,
        channel.id,
        user_id,
    )
    return ChannelConversation(
        **summary.model_dump(),
        organization_id=channel.organization_id,
    )


@router.get("", response_model=ChannelPage)
def get_channels(
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return ChannelPage(
            items=list_channels(
                db,
                current_organization.id,
                current_user.id,
            ),
            can_create=has_permission(db, current_user, "CHANNEL_CREATE"),
        )
    except ValueError as exc:
        _channel_error(exc)


@router.post(
    "",
    response_model=ChannelConversation,
    status_code=status.HTTP_201_CREATED,
)
def post_channel(
    payload: ChannelCreate,
    current_user: User = Depends(require_permission("CHANNEL_CREATE")),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        channel = create_channel(
            db,
            current_organization.id,
            current_user.id,
            payload.name,
            payload.visibility,
        )
        return _conversation_response(db, channel, current_user.id)
    except ValueError as exc:
        _channel_error(exc)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Unable to create the channel",
        ) from exc


@router.post("/{channel_id}/join", response_model=ChannelConversation)
def post_join_channel(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        channel = join_public_channel(
            db,
            current_organization.id,
            channel_id,
            current_user.id,
        )
        return _conversation_response(db, channel, current_user.id)
    except ValueError as exc:
        _channel_error(exc)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Unable to join the channel",
        ) from exc


@router.get(
    "/{channel_id}/members",
    response_model=list[ChannelMemberResponse],
)
def get_channel_members(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return list_channel_members(
            db,
            current_organization.id,
            channel_id,
            current_user.id,
        )
    except ValueError as exc:
        _channel_error(exc)


@router.post(
    "/{channel_id}/members",
    response_model=ChannelMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_channel_member(
    channel_id: int,
    payload: ChannelMemberAdd,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        membership = add_channel_member(
            db,
            current_organization.id,
            channel_id,
            current_user.id,
            payload.user_id,
        )
        return next(
            member
            for member in list_channel_members(
                db,
                current_organization.id,
                channel_id,
                current_user.id,
            )
            if member.user_id == membership.user_id
        )
    except ValueError as exc:
        _channel_error(exc)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Unable to add this channel member",
        ) from exc


@router.patch(
    "/{channel_id}/members/{member_user_id}",
    response_model=ChannelMemberResponse,
)
def patch_channel_member(
    channel_id: int,
    member_user_id: int,
    payload: ChannelMemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        update_channel_member_role(
            db,
            current_organization.id,
            channel_id,
            current_user.id,
            member_user_id,
            payload.role,
        )
        return next(
            member
            for member in list_channel_members(
                db,
                current_organization.id,
                channel_id,
                current_user.id,
            )
            if member.user_id == member_user_id
        )
    except ValueError as exc:
        _channel_error(exc)


@router.delete(
    "/{channel_id}/members/{member_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_channel_member(
    channel_id: int,
    member_user_id: int,
    response: Response,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        remove_channel_member(
            db,
            current_organization.id,
            channel_id,
            current_user.id,
            member_user_id,
        )
        response.status_code = status.HTTP_204_NO_CONTENT
    except ValueError as exc:
        _channel_error(exc)
