from app.core.config import settings


def build_password_reset_email(
    *,
    recipient: str,
    raw_token: str,
) -> tuple[str, str]:
    reset_url = f"{settings.password_reset_url}?token={raw_token}"

    subject = "Reset your NexaWork password"

    body = (
        f"Hello,\n\n"
        f"We received a request to reset your NexaWork password.\n\n"
        f"Reset your password using this link:\n"
        f"{reset_url}\n\n"
        f"This link expires in "
        f"{settings.password_reset_token_expire_minutes} minutes.\n\n"
        f"If you did not request a password reset, you can safely ignore "
        f"this email.\n\n"
        f"— NexaWork"
    )

    return subject, body
