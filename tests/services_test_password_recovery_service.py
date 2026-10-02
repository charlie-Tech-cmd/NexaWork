from tests.helpers import create_password_reset_test_user

from app.services.email.fake import FakeEmailService
from app.services.password_recovery_service import send_password_reset_email


def test_send_password_reset_email_creates_token_and_sends_email(
    db_session,
    monkeypatch,
):
    user = create_password_reset_test_user(db_session)

    monkeypatch.setattr(
        "app.services.password_reset_service.settings.password_reset_token_expire_minutes",
        30,
    )
    monkeypatch.setattr(
        "app.services.email.templates.password_reset.settings.password_reset_url",
        "https://app.example.com/reset-password",
    )

    email_service = FakeEmailService()

    send_password_reset_email(
        db_session,
        user,
        email_service,
    )

    assert len(email_service.sent_emails) == 1

    sent_email = email_service.sent_emails[0]

    assert sent_email["recipient"] == user.email
    assert sent_email["subject"] == "Reset your NexaWork password"
    assert (
        "https://app.example.com/reset-password?token="
        in sent_email["body"]
    )
