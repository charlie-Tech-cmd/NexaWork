from app.services.email.fake import FakeEmailService
from app.services.email.service import EmailService


def get_email_service() -> EmailService:
    return FakeEmailService()
