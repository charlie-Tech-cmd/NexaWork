from app.services.email.fake import FakeEmailService
from app.services.email.service import EmailService
from app.services.email.smtp import SMTPEmailService
from app.core.config import settings


def get_email_service() -> EmailService:
    if settings.email_provider == "smtp":
        return SMTPEmailService(settings)
    return FakeEmailService()
