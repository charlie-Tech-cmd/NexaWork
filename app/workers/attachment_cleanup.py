"""Run explicitly: python -m app.workers.attachment_cleanup --run

Schedule every 15 minutes after deployment approval. Never removes audit history.
"""
import argparse
import logging
from datetime import timedelta
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.attachment import Attachment
from app.services.attachment_service import now, storage

logger = logging.getLogger(__name__)


def cleanup(db, store, limit=100):
    rows = list(db.scalars(select(Attachment).where(Attachment.status.in_(["uploading", "ready", "deleting"]),
        Attachment.expires_at <= now()).order_by(Attachment.expires_at).limit(limit).with_for_update(skip_locked=True)))
    keys = [(row.id, row.storage_key) for row in rows]
    for row in rows:
        row.status = "deleting"
        row.expires_at = now() + timedelta(minutes=15)
    db.commit()
    completed = 0
    for aid, key in keys:
        try:
            store.delete(key)
        except OSError:
            logger.warning("attachment_cleanup_retry attachment_id=%s", aid)
            continue
        row = db.get(Attachment, aid)
        if row and row.status == "deleting":
            row.status, row.deleted_at = "deleted", now()
            db.commit()
            completed += 1
    return completed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", required=True)
    parser.parse_args()
    with SessionLocal() as db:
        print(f"Removed {cleanup(db, storage())} expired/deleting objects")
