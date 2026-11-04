from app.core.security.one_time_token import (
    generate_secure_token,
    hash_token,
)


def generate_reset_token() -> str:
    return generate_secure_token()


def hash_reset_token(token: str) -> str:
    return hash_token(token)
