from app.services.email.service import EmailService


class FakeEmailService(EmailService):
    def __init__(self) -> None:
        self.sent_emails: list[dict[str, str]] = []

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        self.sent_emails.append(
            {
                "recipient": recipient,
                "subject": subject,
                "body": body,
            }
        )
