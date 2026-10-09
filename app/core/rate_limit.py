import redis

from app.core.config import settings
from app.core.redis import check_rate_limit


class RateLimitUnavailable(Exception):
    pass


def _check_rate_limit(
    key: str,
    max_attempts: int,
    window_seconds: int,
) -> bool:
    try:
        return check_rate_limit(key, max_attempts, window_seconds)
    except redis.exceptions.RedisError as exc:
        raise RateLimitUnavailable from exc


def is_login_allowed(key: str) -> bool:
    return _check_rate_limit(
        key,
        settings.rate_limit_max_attempts,
        settings.rate_limit_window_seconds,
    )


def is_login_ip_allowed(key: str) -> bool:
    return _check_rate_limit(
        key,
        settings.rate_limit_ip_max_attempts,
        settings.rate_limit_ip_window_seconds,
    )


def is_password_recovery_allowed(key: str) -> bool:
    return _check_rate_limit(
        key,
        settings.rate_limit_max_attempts,
        settings.rate_limit_window_seconds,
    )
