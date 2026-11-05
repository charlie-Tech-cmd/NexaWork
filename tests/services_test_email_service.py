import smtplib
from unittest.mock import patch

import pytest

from app.api.dependencies_email import get_email_service
from app.core.config import Settings, settings
from app.services.email.fake import FakeEmailService
from app.services.email.smtp import SMTPEmailService


def test_fake_email_service_records_sent_email():
    email_service = FakeEmailService()

    email_service.send(
        recipient="user@example.com",
        subject="Reset your NexaWork password",
        body="Reset link goes here.",
    )

    assert email_service.sent_emails == [
        {
            "recipient": "user@example.com",
            "subject": "Reset your NexaWork password",
            "body": "Reset link goes here.",
        }
    ]


def smtp_settings(**overrides):
    values = {
        "jwt_secret_key": "test-secret-nexawork",
        "email_provider": "smtp",
        "smtp_host": "smtp.example.com",
        "smtp_from_email": "noreply@example.com",
        "smtp_username": "mailer",
        "smtp_password": "smtp-test-password",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_smtp_email_uses_starttls_authentication_and_message_headers():
    config = smtp_settings()
    with patch("app.services.email.smtp.smtplib.SMTP") as smtp_factory:
        client = smtp_factory.return_value.__enter__.return_value
        client.send_message.return_value = {}

        SMTPEmailService(config).send(
            recipient="user@example.com",
            subject="Join NexaWork",
            body="Accept your invitation.",
        )

    smtp_factory.assert_called_once_with(
        "smtp.example.com",
        587,
        timeout=15,
    )
    client.starttls.assert_called_once()
    client.login.assert_called_once_with("mailer", "smtp-test-password")
    message = client.send_message.call_args.args[0]
    assert message["To"] == "user@example.com"
    assert message["From"] == "NexaWork <noreply@example.com>"
    assert message["Subject"] == "Join NexaWork"
    assert message.get_content().strip() == "Accept your invitation."


def test_smtp_email_supports_implicit_tls():
    config = smtp_settings(
        smtp_port=465,
        smtp_use_tls=False,
        smtp_use_ssl=True,
    )
    with patch("app.services.email.smtp.smtplib.SMTP_SSL") as smtp_factory:
        client = smtp_factory.return_value.__enter__.return_value
        client.send_message.return_value = {}

        SMTPEmailService(config).send(
            recipient="user@example.com",
            subject="Subject",
            body="Body",
        )

    assert smtp_factory.call_args.args[:2] == ("smtp.example.com", 465)
    assert "context" in smtp_factory.call_args.kwargs
    client.starttls.assert_not_called()


def test_smtp_email_rejects_unsent_recipient():
    config = smtp_settings()
    with patch("app.services.email.smtp.smtplib.SMTP") as smtp_factory:
        client = smtp_factory.return_value.__enter__.return_value
        client.send_message.return_value = {
            "user@example.com": (550, b"mailbox unavailable")
        }

        with pytest.raises(smtplib.SMTPRecipientsRefused):
            SMTPEmailService(config).send(
                recipient="user@example.com",
                subject="Subject",
                body="Body",
            )


def test_email_dependency_selects_configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "fake")
    assert isinstance(get_email_service(), FakeEmailService)

    monkeypatch.setattr(settings, "email_provider", "smtp")
    assert isinstance(get_email_service(), SMTPEmailService)
