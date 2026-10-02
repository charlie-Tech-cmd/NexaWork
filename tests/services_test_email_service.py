from app.services.email.fake import FakeEmailService


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
