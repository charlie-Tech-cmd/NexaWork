from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.config import settings


def build_password_reset_email(
    *,
    recipient: str,
    raw_token: str,
) -> tuple[str, str]:
    parsed_url = urlsplit(settings.password_reset_url)
    query_params = [
        (key, value)
        for key, value in parse_qsl(
            parsed_url.query,
            keep_blank_values=True,
        )
        if key != "token"
    ]
    query_params.append(("token", raw_token))
    reset_url = urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            urlencode(query_params),
            parsed_url.fragment,
        )
    )

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
