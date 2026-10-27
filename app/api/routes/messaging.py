from fastapi import APIRouter, Depends, HTTPException, Query, status
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
)

router = APIRouter(
    prefix="/api/v1/messaging",
    tags=["messaging"],
)


def _raise_service_error(exc: ValueError) -> None:
    """Translate service errors without disclosing private conversations."""
    if isinstance(exc, ConversationAccessError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc

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
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    current_organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return list_conversations(
            db=db,
            organization_id=current_organization.id,
            user_id=current_user.id,
            limit=limit,
        )
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
    try:
        return send_message(
            db=db,
            organization_id=current_organization.id,
            conversation_id=conversation_id,
            sender_id=current_user.id,
            body=payload.body,
        )
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
        return MessagePage(items=items, next_cursor=next_cursor)
    except ValueError as exc:
        _raise_service_error(exc)
