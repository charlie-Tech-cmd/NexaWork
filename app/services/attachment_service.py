"""Tenant-authorized attachment lifecycle; object I/O never runs inside a DB transaction."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.storage.local import LocalStorage
from app.integrations.storage.service import StorageService
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.conversation_member import ConversationMember
from app.models.organization import Organization
from app.models.user import User
from app.services.messaging_service import ConversationAccessError, MessagingValidationError
from app.services.file_validation import safe_filename, TYPES
from pathlib import Path


class AttachmentConflict(ValueError):
    pass


def now():
    return datetime.now(timezone.utc)


def authorize(db: Session, org_id: int, cid: int, uid: int, *, lock=False, lock_quota=False):
    user_query = select(User).where(
        User.id == uid,
        User.organization_id == org_id,
        User.is_active.is_(True),
        User.is_super_admin.is_(False),
    )
    org_query = select(Organization).where(Organization.id == org_id, Organization.is_active.is_(True))
    member_query = select(ConversationMember).where(
        ConversationMember.organization_id == org_id,
        ConversationMember.conversation_id == cid,
        ConversationMember.user_id == uid,
        ConversationMember.is_active.is_(True),
    )
    if lock:
        # Acquire organization, actor, membership, then attachment locks consistently.
        # The immutable-audit trigger takes FOR UPDATE on the actor: a shared
        # actor lock would deadlock when concurrent audited writes upgrade it.
        user_query = user_query.with_for_update()
        # Quota writers serialize without blocking ordinary foreign-key reads.
        # Take the final lock mode immediately; never upgrade a shared org lock.
        org_query = (org_query.with_for_update(key_share=True) if lock_quota
                     else org_query.with_for_update(read=True))
        member_query = member_query.with_for_update(read=True)
    if db.scalar(org_query) is None or db.scalar(user_query) is None or db.scalar(member_query) is None:
        raise ConversationAccessError("Conversation not found")


def audit(db, org_id, uid, action, attachment):
    db.add(AuditLog(organization_id=org_id, actor_organization_id=org_id, user_id=uid,
                    action=action, resource_type="attachment", resource_id=attachment.id))


def storage() -> StorageService:
    return LocalStorage(settings.storage_local_root)


def reserve(db: Session, org_id: int, cid: int, uid: int, filename: str) -> Attachment:
    filename = safe_filename(filename)
    # Serialize short quota reservations before actor/attachment operations;
    # never retain these locks during upload I/O.
    authorize(db, org_id, cid, uid, lock=True, lock_quota=True)
    in_progress = db.scalar(select(func.count()).select_from(Attachment).where(
        Attachment.organization_id == org_id, Attachment.uploaded_by_user_id == uid,
        Attachment.status.in_(["uploading", "ready"]), Attachment.expires_at > now()))
    if in_progress >= settings.attachment_max_drafts:
        raise AttachmentConflict("Finish or remove your pending files before uploading more")
    used = db.scalar(select(func.coalesce(func.sum(Attachment.size_bytes), 0)).where(
        Attachment.organization_id == org_id, Attachment.created_at > now() - timedelta(days=1)))
    if used + settings.attachment_max_bytes > settings.attachment_org_daily_bytes:
        raise AttachmentConflict("The workspace upload allowance has been reached")
    item = Attachment(organization_id=org_id, conversation_id=cid, uploaded_by_user_id=uid,
        storage_key=uuid4().hex, filename=filename, content_type=TYPES[Path(filename).suffix.lower()],
        size_bytes=settings.attachment_max_bytes, status="uploading", expires_at=now() + timedelta(hours=24))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def finish(db, org_id, cid, uid, aid, size, checksum, content_type):
    authorize(db, org_id, cid, uid, lock=True)
    item = db.scalar(select(Attachment).where(Attachment.id == aid, Attachment.organization_id == org_id,
        Attachment.conversation_id == cid, Attachment.uploaded_by_user_id == uid,
        Attachment.status == "uploading", Attachment.expires_at > now()).with_for_update())
    if item is None:
        raise AttachmentConflict("This upload has expired")
    item.size_bytes, item.sha256, item.content_type, item.status = size, checksum, content_type, "ready"
    audit(db, org_id, uid, "ATTACHMENT_UPLOAD", item)
    db.commit()
    db.refresh(item)
    return item


def get_attachment(db, org_id, cid, uid, aid, *, lock=False):
    authorize(db, org_id, cid, uid, lock=lock)
    query = select(Attachment).where(
        Attachment.id == aid,
        Attachment.organization_id == org_id,
        Attachment.conversation_id == cid,
    )
    item = db.scalar(query.with_for_update() if lock else query)
    if item is None or (item.message_id is None and item.uploaded_by_user_id != uid):
        raise ConversationAccessError("Attachment not found")
    return item


def claim(db, org_id, cid, uid, ids, message_id):
    if len(ids) != len(set(ids)) or len(ids) > settings.attachment_max_per_message:
        raise MessagingValidationError("Attachment IDs must be distinct and within the attachment limit")
    for aid in sorted(ids):
        item = get_attachment(db, org_id, cid, uid, aid, lock=True)
        expiry = item.expires_at.replace(tzinfo=timezone.utc) if item.expires_at.tzinfo is None else item.expires_at
        if item.uploaded_by_user_id != uid or item.status != "ready" or expiry <= now():
            raise AttachmentConflict("A file is unavailable, expired or already shared")
        item.message_id, item.status = message_id, "attached"
        audit(db, org_id, uid, "ATTACHMENT_SHARE", item)


def request_delete(db, org_id, cid, uid, aid):
    item = get_attachment(db, org_id, cid, uid, aid, lock=True)
    if item.uploaded_by_user_id != uid:
        raise PermissionError("Only the uploader can remove this file")
    if item.status not in {"deleting", "deleted"}:
        item.status, item.expires_at = "deleting", now()
        item.deleted_at = now()
        audit(db, org_id, uid, "ATTACHMENT_DELETE_REQUEST", item)
        db.commit()
        db.refresh(item)
    return item


def page(db, org_id, cid, uid, before_id, limit):
    if not 1 <= limit <= 100 or (before_id is not None and before_id <= 0):
        raise MessagingValidationError("Invalid file page parameters")
    authorize(db, org_id, cid, uid)
    query = select(Attachment).where(
        Attachment.organization_id == org_id,
        Attachment.conversation_id == cid,
        Attachment.message_id.is_not(None),
    )
    if before_id:
        query = query.where(Attachment.id < before_id)
    rows = list(db.scalars(query.order_by(Attachment.id.desc()).limit(limit + 1)))
    return rows[:limit], rows[limit - 1].id if len(rows) > limit else None


def for_messages(db, org_id, cid, messages):
    ids = [m.id for m in messages]
    grouped = {mid: [] for mid in ids}
    if ids:
        for item in db.scalars(select(Attachment).where(Attachment.organization_id == org_id,
                Attachment.conversation_id == cid, Attachment.message_id.in_(ids)).order_by(Attachment.id)):
            grouped[item.message_id].append(item)
    return grouped


def abandon(db, org_id, uid, aid):
    """Only known upload reservations; no publication or audit impersonation."""
    db.rollback()
    item = db.scalar(select(Attachment).where(Attachment.id == aid, Attachment.organization_id == org_id,
        Attachment.uploaded_by_user_id == uid, Attachment.status == "uploading").with_for_update())
    if item:
        item.status, item.expires_at, item.size_bytes = "deleting", now(), 0
        db.commit()
        return True
    return False
