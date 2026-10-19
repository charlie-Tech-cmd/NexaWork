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


def test_password_reset_email_url_encodes_token(monkeypatch):
    from urllib.parse import parse_qs, urlsplit

    monkeypatch.setattr(
        settings,
        "password_reset_url",
        "https://app.example.com/reset-password",
    )
    raw_token = "token with+special/chars=="

    _, body = build_password_reset_email(
        recipient="user@example.com",
        raw_token=raw_token,
    )

    reset_link = next(
        line for line in body.splitlines()
        if line.startswith("https://app.example.com/reset-password")
    )
    parsed_url = urlsplit(reset_link)

    assert parse_qs(parsed_url.query)["token"] == [raw_token]


def test_password_reset_email_preserves_existing_query_parameters(
    monkeypatch,
):
    from urllib.parse import parse_qs, urlsplit

    monkeypatch.setattr(
        settings,
        "password_reset_url",
        "https://app.example.com/reset-password?source=email",
    )

    _, body = build_password_reset_email(
        recipient="user@example.com",
        raw_token="test-reset-token",
    )

    reset_link = next(
        line for line in body.splitlines()
        if line.startswith("https://app.example.com/reset-password")
    )
    query = parse_qs(urlsplit(reset_link).query)

    assert query["source"] == ["email"]
    assert query["token"] == ["test-reset-token"]


def test_password_reset_email_replaces_existing_token_parameter(
    monkeypatch,
):
    from urllib.parse import parse_qs, urlsplit

    monkeypatch.setattr(
        settings,
        "password_reset_url",
        "https://app.example.com/reset-password?token=old-token&source=email",
    )

    _, body = build_password_reset_email(
        recipient="user@example.com",
        raw_token="new-token",
    )

    reset_link = next(
        line for line in body.splitlines()
        if line.startswith("https://app.example.com/reset-password")
    )
    query = parse_qs(urlsplit(reset_link).query)

    assert query["token"] == ["new-token"]
    assert query["source"] == ["email"]
