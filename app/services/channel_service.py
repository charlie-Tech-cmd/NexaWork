from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.user import User
from app.schemas.channels import ChannelMemberResponse, ChannelSummary


class ChannelAccessError(ValueError):
    pass


class ChannelValidationError(ValueError):
    pass


def _require_active_user(db: Session, organization_id: int, user_id: int) -> User:
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == organization_id,
            User.is_active.is_(True),
            User.is_super_admin.is_(False),
        )
    )
    if user is None:
        raise ChannelValidationError("User is unavailable in this organization")
    return user


def _channel(
    db: Session,
    organization_id: int,
    channel_id: int,
    *,
    lock: bool = False,
) -> Conversation:
    statement = select(Conversation).where(
        Conversation.id == channel_id,
        Conversation.organization_id == organization_id,
        Conversation.conversation_type == "channel",
    )
    if lock:
        statement = statement.with_for_update()
    channel = db.scalar(statement)
    if channel is None:
        raise ChannelAccessError("Channel not found")
    return channel


def _membership(
    db: Session,
    organization_id: int,
    channel_id: int,
    user_id: int,
) -> ConversationMember:
    membership = db.scalar(
        select(ConversationMember).where(
            ConversationMember.organization_id == organization_id,
            ConversationMember.conversation_id == channel_id,
            ConversationMember.user_id == user_id,
            ConversationMember.is_active.is_(True),
        )
    )
    if membership is None:
        raise ChannelAccessError("Channel not found")
    return membership


def _summaries(
    db: Session,
    channels: list[Conversation],
    user_id: int,
) -> list[ChannelSummary]:
    if not channels:
        return []

    channel_ids = [channel.id for channel in channels]
    organization_id = channels[0].organization_id
    counts = dict(
        db.execute(
            select(
                ConversationMember.conversation_id,
                func.count(ConversationMember.id),
            )
            .join(
                User,
                (User.id == ConversationMember.user_id)
                & (User.organization_id == ConversationMember.organization_id),
            )
            .where(
                ConversationMember.organization_id == organization_id,
                ConversationMember.conversation_id.in_(channel_ids),
                ConversationMember.is_active.is_(True),
                User.is_active.is_(True),
                User.is_super_admin.is_(False),
            )
            .group_by(ConversationMember.conversation_id)
        ).all()
    )
    current_memberships = {
        row.conversation_id: row
        for row in db.scalars(
            select(ConversationMember).where(
                ConversationMember.organization_id == organization_id,
                ConversationMember.conversation_id.in_(channel_ids),
                ConversationMember.user_id == user_id,
                ConversationMember.is_active.is_(True),
            )
        ).all()
    }
    joined_ids = list(current_memberships)
    names: dict[int, list[dict[str, object]]] = {}
    if joined_ids:
        rows = db.execute(
            select(
                ConversationMember.conversation_id,
                User.id,
                User.full_name,
            )
            .join(
                User,
                (User.id == ConversationMember.user_id)
                & (User.organization_id == ConversationMember.organization_id),
            )
            .where(
                ConversationMember.organization_id == organization_id,
                ConversationMember.conversation_id.in_(joined_ids),
                ConversationMember.is_active.is_(True),
                User.is_active.is_(True),
                User.is_super_admin.is_(False),
            )
            .order_by(User.id)
        ).all()
        for conversation_id, member_id, full_name in rows:
            names.setdefault(conversation_id, []).append(
                {"id": member_id, "full_name": full_name}
            )

    results = []
    for channel in channels:
        current = current_memberships.get(channel.id)
        results.append(
            ChannelSummary(
                id=channel.id,
                name=channel.name or "",
                visibility=channel.channel_visibility,
                is_member=current is not None,
                membership_role=(
                    "moderator"
                    if current and current.role == "admin"
                    else "member" if current else None
                ),
                member_count=counts.get(channel.id, 0),
                members=names.get(channel.id, []),
                created_by_user_id=channel.created_by_user_id,
                created_at=channel.created_at,
            )
        )
    return results


def list_channels(
    db: Session,
    organization_id: int,
    user_id: int,
) -> list[ChannelSummary]:
    _require_active_user(db, organization_id, user_id)
    channels = db.scalars(
        select(Conversation)
        .outerjoin(
            ConversationMember,
            (ConversationMember.conversation_id == Conversation.id)
            & (ConversationMember.organization_id == Conversation.organization_id)
            & (ConversationMember.user_id == user_id)
            & ConversationMember.is_active.is_(True),
        )
        .where(
            Conversation.organization_id == organization_id,
            Conversation.conversation_type == "channel",
            (Conversation.channel_visibility == "public")
            | (ConversationMember.id.is_not(None)),
        )
        .order_by(func.lower(Conversation.name), Conversation.id)
    ).all()
    return _summaries(db, channels, user_id)


def channel_summary(
    db: Session,
    organization_id: int,
    channel_id: int,
    user_id: int,
) -> ChannelSummary:
    _require_active_user(db, organization_id, user_id)
    channel = _channel(db, organization_id, channel_id)
    if channel.channel_visibility == "private":
        _membership(db, organization_id, channel_id, user_id)
    return _summaries(db, [channel], user_id)[0]


def create_channel(
    db: Session,
    organization_id: int,
    creator_user_id: int,
    name: str,
    visibility: str,
) -> Conversation:
    _require_active_user(db, organization_id, creator_user_id)
    name = name.strip()
    if not name or len(name) > 255:
        raise ChannelValidationError(
            "Channel name must contain 1 to 255 characters"
        )
    if visibility not in {"public", "private"}:
        raise ChannelValidationError(
            "Channel visibility must be public or private"
        )
    if db.scalar(
        select(Conversation.id).where(
            Conversation.organization_id == organization_id,
            Conversation.conversation_type == "channel",
            func.lower(Conversation.name) == name.lower(),
        )
    ):
        raise ChannelValidationError("A channel with this name already exists")

    channel = Conversation(
        organization_id=organization_id,
        conversation_type="channel",
        name=name,
        channel_visibility=visibility,
        created_by_user_id=creator_user_id,
        direct_user_low_id=None,
        direct_user_high_id=None,
    )
    db.add(channel)
    try:
        db.flush()
        db.add(
            ConversationMember(
                conversation_id=channel.id,
                organization_id=organization_id,
                user_id=creator_user_id,
                role="admin",
                is_active=True,
            )
        )
        db.commit()
        db.refresh(channel)
        return channel
    except IntegrityError as exc:
        db.rollback()
        if "uq_conversations_channel_name" in str(exc):
            raise ChannelValidationError(
                "A channel with this name already exists"
            ) from exc
        raise


def join_public_channel(
    db: Session,
    organization_id: int,
    channel_id: int,
    user_id: int,
) -> Conversation:
    _require_active_user(db, organization_id, user_id)
    channel = _channel(db, organization_id, channel_id)
    if channel.channel_visibility != "public":
        raise ChannelAccessError("Channel not found")
    membership = db.scalar(
        select(ConversationMember).where(
            ConversationMember.organization_id == organization_id,
            ConversationMember.conversation_id == channel_id,
            ConversationMember.user_id == user_id,
        )
    )
    if membership is None:
        db.add(
            ConversationMember(
                conversation_id=channel_id,
                organization_id=organization_id,
                user_id=user_id,
                role="member",
                is_active=True,
            )
        )
    elif not membership.is_active:
        membership.is_active = True
        membership.role = "member"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        membership = db.scalar(
            select(ConversationMember).where(
                ConversationMember.organization_id == organization_id,
                ConversationMember.conversation_id == channel_id,
                ConversationMember.user_id == user_id,
                ConversationMember.is_active.is_(True),
            )
        )
        if membership is None:
            raise
    db.refresh(channel)
    return channel


def list_channel_members(
    db: Session,
    organization_id: int,
    channel_id: int,
    user_id: int,
) -> list[ChannelMemberResponse]:
    _require_active_user(db, organization_id, user_id)
    _channel(db, organization_id, channel_id)
    _membership(db, organization_id, channel_id, user_id)
    rows = db.execute(
        select(ConversationMember, User)
        .join(
            User,
            (User.id == ConversationMember.user_id)
            & (User.organization_id == ConversationMember.organization_id),
        )
        .where(
            ConversationMember.organization_id == organization_id,
            ConversationMember.conversation_id == channel_id,
            ConversationMember.is_active.is_(True),
            User.is_active.is_(True),
            User.is_super_admin.is_(False),
        )
        .order_by(User.full_name, User.id)
    ).all()
    return [
        ChannelMemberResponse(
            user_id=member.user_id,
            full_name=user.full_name,
            role="moderator" if member.role == "admin" else "member",
            joined_at=member.joined_at,
        )
        for member, user in rows
    ]


def _require_moderator(
    db: Session,
    organization_id: int,
    channel_id: int,
    user_id: int,
) -> ConversationMember:
    membership = _membership(db, organization_id, channel_id, user_id)
    if membership.role != "admin":
        raise ChannelAccessError("Channel not found")
    return membership


def add_channel_member(
    db: Session,
    organization_id: int,
    channel_id: int,
    acting_user_id: int,
    member_user_id: int,
) -> ConversationMember:
    _require_active_user(db, organization_id, acting_user_id)
    channel = _channel(db, organization_id, channel_id, lock=True)
    _require_moderator(db, organization_id, channel_id, acting_user_id)
    _require_active_user(db, organization_id, member_user_id)
    existing = db.scalar(
        select(ConversationMember).where(
            ConversationMember.organization_id == organization_id,
            ConversationMember.conversation_id == channel_id,
            ConversationMember.user_id == member_user_id,
        )
    )
    if existing is not None:
        if existing.is_active:
            return existing
        existing.is_active = True
        existing.role = "member"
        db.commit()
        db.refresh(existing)
        return existing
    member_count = db.scalar(
        select(func.count(ConversationMember.id)).where(
            ConversationMember.organization_id == organization_id,
            ConversationMember.conversation_id == channel_id,
            ConversationMember.is_active.is_(True),
        )
    ) or 0
    if member_count >= 500:
        raise ChannelValidationError("A channel can have at most 500 members")
    membership = ConversationMember(
        conversation_id=channel.id,
        organization_id=organization_id,
        user_id=member_user_id,
        role="member",
        is_active=True,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def update_channel_member_role(
    db: Session,
    organization_id: int,
    channel_id: int,
    acting_user_id: int,
    member_user_id: int,
    role: str,
) -> ConversationMember:
    _require_active_user(db, organization_id, acting_user_id)
    _channel(db, organization_id, channel_id, lock=True)
    _require_moderator(db, organization_id, channel_id, acting_user_id)
    membership = _membership(db, organization_id, channel_id, member_user_id)
    if role not in {"member", "moderator"}:
        raise ChannelValidationError(
            "Channel role must be member or moderator"
        )
    if membership.role == "admin" and role == "member":
        moderator_count = db.scalar(
            select(func.count(ConversationMember.id)).where(
                ConversationMember.organization_id == organization_id,
                ConversationMember.conversation_id == channel_id,
                ConversationMember.is_active.is_(True),
                ConversationMember.role == "admin",
            )
        ) or 0
        if moderator_count <= 1:
            raise ChannelValidationError(
                "A channel must keep at least one active moderator"
            )
    membership.role = "admin" if role == "moderator" else "member"
    db.commit()
    db.refresh(membership)
    return membership


def remove_channel_member(
    db: Session,
    organization_id: int,
    channel_id: int,
    acting_user_id: int,
    member_user_id: int,
) -> None:
    _require_active_user(db, organization_id, acting_user_id)
    _channel(db, organization_id, channel_id, lock=True)
    target = _membership(db, organization_id, channel_id, member_user_id)
    if acting_user_id != member_user_id:
        _require_moderator(db, organization_id, channel_id, acting_user_id)
    if target.role == "admin":
        moderator_count = db.scalar(
            select(func.count(ConversationMember.id)).where(
                ConversationMember.organization_id == organization_id,
                ConversationMember.conversation_id == channel_id,
                ConversationMember.is_active.is_(True),
                ConversationMember.role == "admin",
            )
        ) or 0
        if moderator_count <= 1:
            raise ChannelValidationError(
                "A channel must keep at least one active moderator"
            )
    target.is_active = False
    db.commit()
