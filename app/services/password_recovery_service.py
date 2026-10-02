from sqlalchemy.orm import Session

from app.models.user import User
from app.services.email.service import EmailService
from app.services.email.templates.password_reset import (
    build_password_reset_email,
)
from app.services.password_reset_service import create_password_reset_token


def send_password_reset_email(
    db: Session,
    user: User,
    email_service: EmailService,
) -> None:
    raw_token, _ = create_password_reset_token(
        db,
        user,
    )

    subject, body = build_password_reset_email(
        recipient=user.email,
        raw_token=raw_token,
    )

    email_service.send(
        recipient=user.email,
        subject=subject,
        body=body,
    )
