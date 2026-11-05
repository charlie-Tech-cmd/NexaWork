import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings, settings
from app.services.email.service import EmailService


class SMTPEmailService(EmailService):
    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    def send(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = formataddr(
            (self.config.smtp_from_name, self.config.smtp_from_email)
        )
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        if self.config.smtp_use_ssl:
            connection = smtplib.SMTP_SSL(
                self.config.smtp_host,
                self.config.smtp_port,
                timeout=self.config.smtp_timeout_seconds,
                context=ssl.create_default_context(),
            )
        else:
            connection = smtplib.SMTP(
                self.config.smtp_host,
                self.config.smtp_port,
                timeout=self.config.smtp_timeout_seconds,
            )

        with connection as client:
            if self.config.smtp_use_tls:
                client.starttls(context=ssl.create_default_context())
            if self.config.smtp_username:
                client.login(
                    self.config.smtp_username,
                    self.config.smtp_password,
                )
            refused = client.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
