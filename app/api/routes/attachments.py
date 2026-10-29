import asyncio
import hashlib
from typing import Annotated
from urllib.parse import quote, unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Path
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_current_organization
from app.db.session import get_db
from app.core.config import settings
from app.models.user import User
from app.models.organization import Organization
from app.schemas.attachment import AttachmentResponse, AttachmentPage
from app.services import attachment_service as service
from app.services.file_validation import FileRejected, validate_content, scan_file
from app.services.messaging_service import ConversationAccessError, MessagingValidationError
from app.core.redis import check_rate_limit
from redis.exceptions import RedisError

router = APIRouter(prefix="/api/v1/messaging", tags=["attachments"])


class PrivateFileResponse(StreamingResponse):
    def __init__(self, stream, *args, **kwargs):
        self.private_stream = stream
        super().__init__(*args, **kwargs)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.private_stream.close()


def available():
    if not settings.attachments_enabled:
        raise HTTPException(503, "File sharing is not configured for this workspace")


def translate(exc):
    if isinstance(exc, ConversationAccessError):
        return HTTPException(404, "Conversation or file not found")
    if isinstance(exc, MessagingValidationError):
        return HTTPException(400, str(exc))
    if isinstance(exc, service.AttachmentConflict):
        return HTTPException(409, str(exc))
    if isinstance(exc, UnicodeError):
        return HTTPException(422, "Filename must be valid encoded UTF-8")
    if isinstance(exc, FileRejected):
        return HTTPException(415, str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(403, str(exc))
    return HTTPException(503, "File storage or safety scanning is temporarily unavailable")


@router.get("/file-policy")
def policy(user: User = Depends(get_current_user)):
    return {"enabled": settings.attachments_enabled, "max_bytes": settings.attachment_max_bytes,
            "max_attachments": settings.attachment_max_per_message, "extensions": [
                ".txt",
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
            ]}


@router.post(
    "/conversations/{cid}/attachments",
    response_model=AttachmentResponse,
    status_code=201,
    openapi_extra={"requestBody": {"required": True, "content": {
        "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
    }}},
)
async def upload(cid: Annotated[int, Path(gt=0)], request: Request, x_filename: str = Header(max_length=3000),
                 user: User = Depends(get_current_user), org: Organization = Depends(get_current_organization),
                 db: Session = Depends(get_db)):
    available()
    org_id, uid = org.id, user.id
    if cid <= 0:
        raise HTTPException(422, "Invalid conversation ID")
    if settings.messaging_rate_limits_enabled:
        try:
            allowed = await run_in_threadpool(check_rate_limit, f"messaging:upload:{org_id}:{uid}", 10, 60)
        except RedisError as exc:
            raise HTTPException(503, "Upload protection is temporarily unavailable") from exc
        if not allowed:
            raise HTTPException(429, "Too many uploads. Please wait", headers={"Retry-After": "60"})
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > settings.attachment_max_bytes):
        raise HTTPException(413, "The file exceeds the upload limit")
    item = None
    item_id = None
    object_key = None
    store = None
    writer = None
    try:
        item = await run_in_threadpool(service.reserve, db, org_id, cid, uid, unquote(x_filename, errors="strict"))
        item_id, object_key = item.id, item.storage_key
        # The database reservation has committed before opening storage.
        store = service.storage()
        writer = await run_in_threadpool(store.create, object_key)
        size, digest = 0, hashlib.sha256()
        async with asyncio.timeout(settings.attachment_upload_timeout):
            async for chunk in request.stream():
                size += len(chunk)
                if size > settings.attachment_max_bytes:
                    raise HTTPException(413, "The file exceeds the upload limit")
                digest.update(chunk)
                await run_in_threadpool(writer.write, chunk)
        await run_in_threadpool(writer.close)
        writer = None
        if not size:
            raise FileRejected("Empty files cannot be shared")
        def inspect_file():
            with store.open(object_key) as stream:
                content_type = validate_content(stream, item.filename)
                if settings.file_scan_host:
                    try:
                        scan_file(
                            stream,
                            settings.file_scan_host,
                            settings.file_scan_port,
                            settings.file_scan_timeout,
                        )
                    except OSError as exc:
                        raise OSError("Safety scan unavailable") from exc
                elif not settings.allow_unscanned_development_files:
                    raise OSError("Scanner not configured")
                return content_type
        content_type = await run_in_threadpool(inspect_file)
        return await run_in_threadpool(
            service.finish,
            db,
            org_id,
            cid,
            uid,
            item_id,
            size,
            digest.hexdigest(),
            content_type,
        )
    except BaseException as exc:
        # Cancellation/disconnects leave a durable cleanup target even if delete fails.
        if writer:
            try:
                await run_in_threadpool(writer.close)
            except OSError:
                pass  # The persisted reservation still allows cleanup.
        await run_in_threadpool(db.rollback)
        delete_object = False
        if item_id is not None:
            try:
                delete_object = await run_in_threadpool(service.abandon, db, org_id, uid, item_id)
            except Exception:
                await run_in_threadpool(db.rollback)
        # A cancellation after final commit must not delete an already-ready object.
        if delete_object and store:
            try:
                await run_in_threadpool(store.delete, object_key)
            except OSError:
                pass  # Expired reservation remains for the cleanup runner.
        if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, TimeoutError):
            raise HTTPException(408, "Upload timed out. Please try again") from exc
        raise translate(exc) from exc


@router.get("/conversations/{cid}/attachments", response_model=AttachmentPage)
def list_files(cid: Annotated[
    int,
    Path(gt=0),
], before_id: int | None = Query(
    None,
    gt=0,
), limit: int = Query(
    50,
    ge=1,
    le=100,
),
               user: User = Depends(get_current_user), org: Organization = Depends(get_current_organization), db: Session = Depends(get_db)):
    try:
        items, cursor = service.page(db, org.id, cid, user.id, before_id, limit)
        return AttachmentPage(items=items, next_cursor=cursor)
    except ValueError as exc:
        raise translate(exc) from exc


@router.get("/conversations/{cid}/attachments/{aid}", response_model=AttachmentResponse)
def metadata(
    cid: Annotated[int, Path(gt=0)],
    aid: Annotated[int, Path(gt=0)],
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return service.get_attachment(db, org.id, cid, user.id, aid)
    except ValueError as exc:
        raise translate(exc) from exc


@router.get("/conversations/{cid}/attachments/{aid}/download")
def download(
    cid: Annotated[int, Path(gt=0)],
    aid: Annotated[int, Path(gt=0)],
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    if settings.messaging_rate_limits_enabled:
        try:
            allowed = check_rate_limit(f"messaging:download:{org.id}:{user.id}", 120, 60)
        except RedisError as exc:
            raise HTTPException(503, "Download protection is temporarily unavailable") from exc
        if not allowed:
            raise HTTPException(429, "Too many downloads. Please wait", headers={"Retry-After": "60"})
    try:
        item = service.get_attachment(db, org.id, cid, user.id, aid, lock=True)
        if item.status in {"deleting", "deleted"}:
            raise HTTPException(410, "This file was removed")
        if item.status != "attached":
            raise HTTPException(409, "This file has not been shared yet")
        stream = service.storage().open(item.storage_key)
        try:
            service.audit(db, org.id, user.id, "ATTACHMENT_DOWNLOAD_GRANTED", item)
            db.commit()
        except BaseException:
            stream.close()
            raise
        def chunks():
            try:
                while chunk := stream.read(65536):
                    yield chunk
            finally:
                stream.close()
        return PrivateFileResponse(stream, chunks(), media_type=item.content_type, headers={
            "Content-Disposition": f"attachment; filename=download; filename*=UTF-8''{quote(
                item.filename,
                safe='',
            )}",
            "Content-Length": str(item.size_bytes), "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
    except HTTPException:
        raise
    except (ValueError, OSError) as exc:
        raise translate(exc) from exc


@router.delete("/conversations/{cid}/attachments/{aid}", response_model=AttachmentResponse, status_code=202)
def remove(
    cid: Annotated[int, Path(gt=0)],
    aid: Annotated[int, Path(gt=0)],
    user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    try:
        return service.request_delete(db, org.id, cid, user.id, aid)
    except (ValueError, PermissionError) as exc:
        raise translate(exc) from exc
