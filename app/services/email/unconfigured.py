from app.services.email.service import (
    EmailDeliveryUnavailable,
    EmailService,
)


class UnconfiguredEmailService(EmailService):
    def ensure_available(self) -> None:
        raise EmailDeliveryUnavailable(
            "Email delivery is not configured for this environment"
        )

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        self.ensure_available()
