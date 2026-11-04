from app.core.config import settings
from app.services.email.fake import FakeEmailService
from app.services.email.service import EmailService
from app.services.email.unconfigured import UnconfiguredEmailService


def get_email_service() -> EmailService:
    if (
        settings.email_provider == "fake"
        and settings.environment.strip().lower() in {"development", "test"}
    ):
        return FakeEmailService()
    return UnconfiguredEmailService()
