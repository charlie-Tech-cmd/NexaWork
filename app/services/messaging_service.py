"""Tenant-scoped messaging operations.

Authorization is enforced here independently of the API routes.
"""

from sqlalchemy import select, or_, and_
import base64
import hashlib
import hmac
import json
from datetime import datetime
from app.core.config import settings
from app.models.organization import Organization
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.user import User


class MessagingValidationError(ValueError):
    pass


class ConversationAccessError(ValueError):
    pass


def _is_direct_pair_unique_violation(exc: IntegrityError) -> bool:
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint == "uq_conversations_direct_pair":
        return True

    sqlite_message = (
        "UNIQUE constraint failed: conversations.organization_id, "
        "conversations.direct_user_low_id, conversations.direct_user_high_id"
    )
    return sqlite_message in str(exc.orig)


def _require_active_user(
    db: Session,
    organization_id: int,
    user_id: int,
) -> User:
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
            User.is_super_admin.is_(False),
        )
    )
    if user is None:
        raise MessagingValidationError("User is unavailable in this organization")
    return user


def _require_active_membership(
    db: Session,
    organization_id: int,
    conversation_id: int,
    user_id: int,
) -> ConversationMember:
    membership = db.scalar(
        select(ConversationMember).where(
            ConversationMember.organization_id == organization_id,
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user_id,
            ConversationMember.is_active.is_(True),
        )
    )
    if membership is None:
        raise ConversationAccessError("Conversation not found or access denied")
    return membership


def create_or_get_direct_conversation(
    db: Session,
    organization_id: int,
    creator_user_id: int,
    recipient_user_id: int,
) -> Conversation:
    """Create a direct conversation or return the existing pair."""
    _require_active_user(db, organization_id, creator_user_id)
    _require_active_user(db, organization_id, recipient_user_id)

    if creator_user_id == recipient_user_id:
        raise MessagingValidationError("Cannot create a direct conversation with yourself")

    low_id, high_id = sorted((creator_user_id, recipient_user_id))

    def find_existing() -> Conversation | None:
        return db.scalar(
            select(Conversation).where(
                Conversation.organization_id == organization_id,
                Conversation.conversation_type == "direct",
                Conversation.direct_user_low_id == low_id,
                Conversation.direct_user_high_id == high_id,
            )
        )

    existing = find_existing()
    if existing is not None:
        member_ids = set(
            db.scalars(
                select(ConversationMember.user_id).where(
                    ConversationMember.organization_id == organization_id,
                    ConversationMember.conversation_id == existing.id,
                    ConversationMember.user_id.in_([low_id, high_id]),
                    ConversationMember.is_active.is_(True),
                )
            ).all()
        )
        if member_ids != {low_id, high_id}:
            raise ConversationAccessError(
                "Direct conversation has an inactive membership"
            )
        return existing

    conversation = Conversation(
        organization_id=organization_id,
        conversation_type="direct",
        created_by_user_id=creator_user_id,
        direct_user_low_id=low_id,
        direct_user_high_id=high_id,
        name=None,
    )
    db.add(conversation)

    try:
        db.flush()
        db.add_all(
            [
                ConversationMember(
                    conversation_id=conversation.id,
                    organization_id=organization_id,
                    user_id=low_id,
                    role="member",
                    is_active=True,
                ),
                ConversationMember(
                    conversation_id=conversation.id,
                    organization_id=organization_id,
                    user_id=high_id,
                    role="member",
                    is_active=True,
                ),
            ]
        )
        db.commit()
        db.refresh(conversation)
        return conversation
    except IntegrityError as exc:
        db.rollback()

        if not _is_direct_pair_unique_violation(exc):
            raise

        # Recover only when the competing transaction created a complete pair.
        existing = find_existing()
        if existing is None:
            raise

        member_ids = set(
            db.scalars(
                select(ConversationMember.user_id).where(
                    ConversationMember.organization_id == organization_id,
                    ConversationMember.conversation_id == existing.id,
                    ConversationMember.user_id.in_([low_id, high_id]),
                    ConversationMember.is_active.is_(True),
                )
            ).all()
        )
        if member_ids != {low_id, high_id}:
            raise
        return existing


def create_group_conversation(
    db: Session,
    organization_id: int,
    creator_user_id: int,
    name: str,
    member_user_ids: list[int],
) -> Conversation:
    """Create a group and add its creator as an administrator."""
    _require_active_user(db, organization_id, creator_user_id)

    name = name.strip()
    if not name or len(name) > 255:
        raise MessagingValidationError("Group name must contain 1 to 255 characters")

    if any(user_id <= 0 for user_id in member_user_ids):
        raise MessagingValidationError("Member IDs must be positive integers")

    if len(member_user_ids) != len(set(member_user_ids)):
        raise MessagingValidationError("Member IDs must not contain duplicates")

    # The creator counts toward the maximum of 100 total members.
    all_member_ids = set(member_user_ids)
    all_member_ids.add(creator_user_id)
    if len(all_member_ids) > 100:
        raise MessagingValidationError("A group can contain at most 100 total members")

    active_users = db.scalars(
        select(User.id).where(
            User.organization_id == organization_id,
            User.is_active.is_(True),
            User.is_super_admin.is_(False),
            User.id.in_(all_member_ids),
        )
    ).all()

    if set(active_users) != all_member_ids:
        raise MessagingValidationError("One or more members are unavailable in this organization")

    conversation = Conversation(
        organization_id=organization_id,
        conversation_type="group",
        name=name,
        created_by_user_id=creator_user_id,
        direct_user_low_id=None,
        direct_user_high_id=None,
    )
    db.add(conversation)

    try:
        db.flush()
        db.add_all(
            [
                ConversationMember(
                    conversation_id=conversation.id,
                    organization_id=organization_id,
                    user_id=user_id,
                    role="admin" if user_id == creator_user_id else "member",
                    is_active=True,
                )
                for user_id in sorted(all_member_ids)
            ]
        )
        db.commit()
        db.refresh(conversation)
        return conversation
    except IntegrityError:
        db.rollback()
        raise


def list_conversations(
    db: Session,
    organization_id: int,
    user_id: int,
    limit: int = 50,
) -> list[Conversation]:
    """List only conversations the user can currently access."""
    _require_active_user(db, organization_id, user_id)

    if not 1 <= limit <= 100:
        raise MessagingValidationError("Limit must be between 1 and 100")

    statement = (
        select(Conversation)
        .join(
            ConversationMember,
            (ConversationMember.conversation_id == Conversation.id)
            & (ConversationMember.organization_id == Conversation.organization_id),
        )
        .where(
            Conversation.organization_id == organization_id,
            ConversationMember.user_id == user_id,
            ConversationMember.is_active.is_(True),
        )
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def send_message(
    db: Session,
    organization_id: int,
    conversation_id: int,
    sender_id: int,
    body: str,
    attachment_ids: list[int] | None = None,
    client_message_id: str | None = None,
) -> Message:
    """Send a message only as an active member of the conversation."""
    _require_active_user(db, organization_id, sender_id)
    _require_active_membership(
        db, organization_id, conversation_id, sender_id
    )

    body = body.strip()
    if not body:
        raise MessagingValidationError("Message body cannot be blank")
    if len(body) > 10000:
        raise MessagingValidationError("Message body exceeds 10000 characters")

    from app.services.attachment_service import authorize, claim, AttachmentConflict
    authorize(db, organization_id, conversation_id, sender_id, lock=True)
    ids = attachment_ids or []
    if ids and not settings.attachments_enabled:
        raise MessagingValidationError("File sharing is currently disabled")
    fingerprint = hashlib.sha256(json.dumps([body, sorted(ids)], separators=(",", ":")).encode()).hexdigest()

    def existing_request():
        return db.scalar(select(Message).where(Message.organization_id == organization_id,
            Message.conversation_id == conversation_id, Message.sender_id == sender_id,
            Message.client_message_id == client_message_id)) if client_message_id else None

    existing = existing_request()
    if existing:
        if existing.request_hash != fingerprint:
            raise AttachmentConflict("This send identifier was already used for a different message")
        return existing
    message = Message(conversation_id=conversation_id, organization_id=organization_id,
                      sender_id=sender_id, body=body, client_message_id=client_message_id,
                      request_hash=fingerprint if client_message_id else None)
    try:
        db.add(message)
        db.flush()
        claim(db, organization_id, conversation_id, sender_id, ids, message.id)
        db.commit()
        db.refresh(message)
        return message
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        duplicate = constraint == "uq_messages_client_request" or (
            "UNIQUE constraint failed: messages.organization_id, messages.conversation_id, messages.sender_id, messages.client_message_id" in str(exc.orig))
        if duplicate and client_message_id:
            # Reauthorize after rollback; do not reveal a result after revocation.
            authorize(db, organization_id, conversation_id, sender_id, lock=True)
            existing = existing_request()
            if existing and existing.request_hash == fingerprint:
                return existing
            raise AttachmentConflict("Conflicting message retry") from exc
        raise
    except Exception:
        db.rollback()
        raise


def list_messages(
    db: Session,
    organization_id: int,
    conversation_id: int,
    user_id: int,
    before_id: int | None = None,
    limit: int = 50,
) -> tuple[list[Message], int | None]:
    """Return a chronological page and a cursor for older messages."""
    _require_active_user(db, organization_id, user_id)
    _require_active_membership(
        db, organization_id, conversation_id, user_id
    )

    if not 1 <= limit <= 100:
        raise MessagingValidationError("Limit must be between 1 and 100")
    if before_id is not None and before_id <= 0:
        raise MessagingValidationError("Cursor must be a positive message ID")

    statement = select(Message).where(
        Message.organization_id == organization_id,
        Message.conversation_id == conversation_id,
    )
    if before_id is not None:
        statement = statement.where(Message.id < before_id)

    descending = list(
        db.scalars(
            statement.order_by(Message.id.desc()).limit(limit + 1)
        ).all()
    )

    has_more = len(descending) > limit
    page_descending = descending[:limit]
    next_cursor = page_descending[-1].id if has_more and page_descending else None

    # Return oldest-to-newest within this page for normal chat rendering.
    page = list(reversed(page_descending))
    return page, next_cursor


def conversation_page(db, organization_id, user_id, limit=50, cursor=None):
    if not 1 <= limit <= 100:
        raise MessagingValidationError("Limit must be between 1 and 100")
    _require_active_user(db, organization_id, user_id)
    query = select(Conversation).join(ConversationMember,
        (ConversationMember.conversation_id == Conversation.id) &
        (ConversationMember.organization_id == Conversation.organization_id)).where(
        Conversation.organization_id == organization_id, ConversationMember.user_id == user_id,
        ConversationMember.is_active.is_(True))
    if cursor:
        try:
            data, signature = cursor.split(".")
            expected = hmac.new(
                settings.jwt_secret_key.encode(),
                ("conversation-page:" + data).encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError()
            payload = json.loads(base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)))
            if payload["v"] != 1 or payload["org"] != organization_id or payload["user"] != user_id or type(payload["id"]) is not int or payload["id"] <= 0:
                raise ValueError()
            stamp, cid = datetime.fromisoformat(payload["time"]), payload["id"]
            query = query.where(or_(Conversation.created_at < stamp,
                and_(Conversation.created_at == stamp, Conversation.id < cid)))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise MessagingValidationError("Invalid conversation cursor") from exc
    rows = list(db.scalars(query.order_by(
        Conversation.created_at.desc(),
        Conversation.id.desc(),
    ).limit(limit + 1)))
    items = rows[:limit]
    next_cursor = None
    if len(rows) > limit:
        last = items[-1]
        data = base64.urlsafe_b64encode(json.dumps({"v": 1, "org": organization_id, "user": user_id,
            "time": last.created_at.isoformat(), "id": last.id}, separators=(
                ",",
                ":",
            )).encode()).decode().rstrip("=")
        signature = hmac.new(
            settings.jwt_secret_key.encode(),
            ("conversation-page:" + data).encode(),
            hashlib.sha256,
        ).hexdigest()
        next_cursor = data + "." + signature
    return items, next_cursor


def conversation_members(db, organization_id, conversation_ids):
    result = {cid: [] for cid in conversation_ids}
    if conversation_ids:
        for cid, uid, name in db.execute(select(ConversationMember.conversation_id, User.id, User.full_name)
                .join(
                    User,
                    (User.id == ConversationMember.user_id) & (User.organization_id == ConversationMember.organization_id),
                )
                .where(ConversationMember.organization_id == organization_id, ConversationMember.conversation_id.in_(conversation_ids),
                       ConversationMember.is_active.is_(True), User.is_active.is_(True)).order_by(User.id)):
            result[cid].append({"id": uid, "full_name": name})
    return result
