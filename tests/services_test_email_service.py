import pytest

from app.services.email.fake import FakeEmailService
from app.services.email.service import EmailDeliveryUnavailable
from app.services.email.unconfigured import UnconfiguredEmailService
from app.api.dependencies_email import get_email_service


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


def test_email_dependency_never_uses_fake_provider_outside_dev_or_test(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.api.dependencies_email.settings.environment",
        "production",
    )
    monkeypatch.setattr(
        "app.api.dependencies_email.settings.email_provider",
        "unconfigured",
    )

    email_service = get_email_service()

    assert isinstance(email_service, UnconfiguredEmailService)
    with pytest.raises(EmailDeliveryUnavailable):
        email_service.ensure_available()
