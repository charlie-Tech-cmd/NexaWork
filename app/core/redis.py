import redis

from app.core.config import settings


redis_client = redis.Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


def set_value(key: str, value: str, expire_seconds: int | None = None) -> None:
    redis_client.set(key, value, ex=expire_seconds)


def get_value(key: str) -> str | None:
    return redis_client.get(key)


def increment_value(key: str) -> int:
    return int(redis_client.incr(key))


def expire_key(key: str, expire_seconds: int) -> None:
    redis_client.expire(key, expire_seconds)

