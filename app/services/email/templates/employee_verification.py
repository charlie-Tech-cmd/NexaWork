from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.config import settings


def build_employee_verification_email(
    *,
    raw_token: str,
) -> tuple[str, str]:
    parsed_url = urlsplit(settings.email_verification_url)
    query_params = [
        (key, value)
        for key, value in parse_qsl(
            parsed_url.query,
            keep_blank_values=True,
        )
        if key != "token"
    ]
    query_params.append(("token", raw_token))
    verification_url = urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            urlencode(query_params),
            parsed_url.fragment,
        )
    )

    subject = "Verify your NexaWork email"
    body = (
        "Hello,\n\n"
        "Verify your email address to continue your NexaWork registration:\n"
        f"{verification_url}\n\n"
        "Your registration remains pending until an organization "
        "administrator approves it. This link expires in "
        f"{settings.email_verification_token_expire_minutes} minutes.\n\n"
        "If you did not request this registration, you can ignore this email.\n\n"
        "NexaWork"
    )
    return subject, body
