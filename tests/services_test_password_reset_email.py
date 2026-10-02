from app.core.config import settings
from app.services.email.templates.password_reset import (
    build_password_reset_email,
)


def test_build_password_reset_email_uses_configured_url(monkeypatch):
    monkeypatch.setattr(
        settings,
        "password_reset_url",
        "https://app.example.com/reset-password",
    )
    monkeypatch.setattr(
        settings,
        "password_reset_token_expire_minutes",
        30,
    )

    raw_token = "test-reset-token"

    subject, body = build_password_reset_email(
        recipient="user@example.com",
        raw_token=raw_token,
    )

    assert subject == "Reset your NexaWork password"
    assert (
        "https://app.example.com/reset-password"
        "?token=test-reset-token"
    ) in body
    assert "30 minutes" in body
    assert "If you did not request a password reset" in body
