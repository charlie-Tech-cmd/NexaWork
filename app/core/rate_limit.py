from app.core.config import settings
from app.core.redis import check_rate_limit


def is_login_allowed(key: str) -> bool:
    return check_rate_limit(
        key,
        settings.rate_limit_max_attempts,
        settings.rate_limit_window_seconds,
    )
