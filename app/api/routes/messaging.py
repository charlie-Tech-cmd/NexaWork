from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_organization,
    get_current_user,
)
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.messaging import (
    ConversationResponse,
    ConversationSummary, ConversationPage, MessagingPerson,
    DirectConversationCreate,
    GroupConversationCreate,
    MessageCreate,
    MessagePage,
    MessageResponse,
)
from app.services.messaging_service import (
    ConversationAccessError,
    MessagingValidationError,
    create_group_conversation,
    create_or_get_direct_conversation,
    list_conversations,
    list_messages,
    send_message,
    conversation_page, conversation_members,
)

router = APIRouter(
    prefix="/api/v1/messaging",
    tags=["messaging"],
)


def protect_write(org_id, user_id, action, maximum):
    from app.core.config import settings
    if settings.messaging_rate_limits_enabled:
        from app.core.redis import check_rate_limit
        from redis.exceptions import RedisError
        try:
            allowed = check_rate_limit(f"messaging:{action}:{org_id}:{user_id}", maximum, 60)
        except RedisError as exc:
            raise HTTPException(503, "Messaging protection is temporarily unavailable") from exc
        if not allowed:
            raise HTTPException(429, "Too many requests. Please wait", headers={"Retry-After": "60"})


def _raise_service_error(exc: ValueError) -> None:
    """Translate service errors without disclosing private conversations."""
    if isinstance(exc, ConversationAccessError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc

    from app.services.attachment_service import AttachmentConflict
    if isinstance(exc, AttachmentConflict):
        raise HTTPException(409, str(exc)) from exc
    if isinstance(exc, MessagingValidationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal messaging error",
    ) from exc


@router.post(
    "/direct",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
def create_direct_conversation(
    payload: DirectConversationCreate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    protect_write(current_organization.id, current_user.id, "create", 20)
    try:
        return create_or_get_direct_conversation(
            db=db,
            organization_id=current_organization.id,
            creator_user_id=current_user.id,
            recipient_user_id=payload.recipient_user_id,
        )
    except ValueError as exc:
        _raise_service_error(exc)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create the conversation",
        ) from exc


@router.post(
    "/groups",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    payload: GroupConversationCreate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    protect_write(current_organization.id, current_user.id, "create", 20)
    try:
        return create_group_conversation(
            db=db,
            organization_id=current_organization.id,
            creator_user_id=current_user.id,
            name=payload.name,
            member_user_ids=payload.member_user_ids,
        )
    except ValueError as exc:
        _raise_service_error(exc)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create the group conversation",
        ) from exc


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
)
def get_conversations(
    response: Response,
    cursor: str | None = Query(None, max_length=1024),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        items, next_cursor = conversation_page(db, current_organization.id, current_user.id, limit, cursor)
        if next_cursor:
            response.headers["Link"] = f'</api/v1/messaging/conversations?limit={limit}&cursor={next_cursor}>; rel="next"'
        return items
    except ValueError as exc:
        _raise_service_error(exc)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    conversation_id: int,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    protect_write(current_organization.id, current_user.id, "send", 60)
    try:
        message = send_message(
            db=db,
            organization_id=current_organization.id,
            conversation_id=conversation_id,
            sender_id=current_user.id,
            body=payload.body,
            attachment_ids=payload.attachment_ids,
            client_message_id=str(payload.client_message_id) if payload.client_message_id else None,
        )
        return message_responses(db, current_organization.id, conversation_id, [message])[0]
    except ValueError as exc:
        _raise_service_error(exc)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to send the message",
        ) from exc


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePage,
)
def get_messages(
    conversation_id: int,
    before_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        items, next_cursor = list_messages(
            db=db,
            organization_id=current_organization.id,
            conversation_id=conversation_id,
            user_id=current_user.id,
            before_id=before_id,
            limit=limit,
        )
        return MessagePage(
            items=message_responses(db, current_organization.id, conversation_id, items),
            next_cursor=next_cursor,
        )
    except ValueError as exc:
        _raise_service_error(exc)


def message_responses(db, org_id, cid, messages):
    from app.services.attachment_service import for_messages
    from app.schemas.attachment import AttachmentResponse
    files = for_messages(db, org_id, cid, messages)
    return [MessageResponse.model_validate(message).model_copy(update={"attachments": [AttachmentResponse.model_validate(a) for a in files[message.id]]}) for message in messages]


@router.get("/conversations/page", response_model=ConversationPage)
def get_conversation_page(limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, max_length=1024),
                          current_user: User = Depends(get_current_user), current_organization: Organization = Depends(get_current_organization),
                          db: Session = Depends(get_db)):
    try:
        rows, next_cursor = conversation_page(db, current_organization.id, current_user.id, limit, cursor)
        members = conversation_members(db, current_organization.id, [c.id for c in rows])
        return ConversationPage(
            items=[ConversationSummary.model_validate(c).model_copy(update={"members": [MessagingPerson.model_validate(person) for person in members[c.id]]}) for c in rows],
            next_cursor=next_cursor,
        )
    except ValueError as exc:
        _raise_service_error(exc)


@router.get("/people", response_model=list[MessagingPerson])
def messaging_people(search: str = Query(
    "",
    max_length=100,
), after_id: int = Query(
    0,
    ge=0,
), limit: int = Query(
    20,
    ge=1,
    le=100,
),
                     current_user: User = Depends(get_current_user), current_organization: Organization = Depends(get_current_organization), db: Session = Depends(get_db)):
    from sqlalchemy import select
    statement = select(User).where(User.organization_id == current_organization.id, User.is_active.is_(True),
        User.is_super_admin.is_(False), User.id != current_user.id, User.id > after_id)
    if search.strip():
        statement = statement.where(User.full_name.contains(search.strip(), autoescape=True))
    return [{"id": u.id, "full_name": u.full_name} for u in db.scalars(statement.order_by(User.id).limit(limit))]


@router.get("/conversations/{conversation_id}/updates", response_model=MessagePage)
def get_updates(conversation_id: int, after_id: int = Query(..., gt=0), limit: int = Query(50, ge=1, le=100),
                current_user: User = Depends(get_current_user), current_organization: Organization = Depends(get_current_organization),
                db: Session = Depends(get_db)):
    from sqlalchemy import select
    from app.models.message import Message
    from app.services.attachment_service import authorize
    try:
        authorize(db, current_organization.id, conversation_id, current_user.id)
        rows = list(db.scalars(select(Message).where(Message.organization_id == current_organization.id,
            Message.conversation_id == conversation_id, Message.id > after_id).order_by(Message.id).limit(limit + 1)))
        items = rows[:limit]
        return MessagePage(
            items=message_responses(db, current_organization.id, conversation_id, items),
            next_cursor=items[-1].id if len(rows) > limit else None,
        )
    except ValueError as exc:
        _raise_service_error(exc)
