from app.core.redis import redis_client


def test_redis_client_uses_configured_url():
    from redis.connection import parse_url

    from app.core.config import settings

    expected = parse_url(settings.redis_url)
    actual = redis_client.connection_pool.connection_kwargs

    assert actual["host"] == expected["host"]
    assert actual["port"] == expected["port"]

def test_set_value_uses_expiration(monkeypatch):
    calls = []

    def fake_set(key, value, ex=None):
        calls.append((key, value, ex))

    monkeypatch.setattr(redis_client, "set", fake_set)

    from app.core.redis import set_value

    set_value("test:key", "1", expire_seconds=60)

    assert calls == [("test:key", "1", 60)]


def test_get_value_returns_redis_value(monkeypatch):
    monkeypatch.setattr(redis_client, "get", lambda key: "stored-value")

    from app.core.redis import get_value

    assert get_value("test:key") == "stored-value"


def test_increment_value_returns_integer(monkeypatch):
    monkeypatch.setattr(redis_client, "incr", lambda key: 3)

    from app.core.redis import increment_value

    assert increment_value("test:key") == 3


def test_expire_key_sets_expiration(monkeypatch):
    calls = []

    def fake_expire(key, seconds):
        calls.append((key, seconds))

    monkeypatch.setattr(redis_client, "expire", fake_expire)

    from app.core.redis import expire_key

    expire_key("test:key", 60)

    assert calls == [("test:key", 60)]


def test_rate_limit_allows_attempt_within_limit(monkeypatch):
    calls = []

    def fake_eval(script, numkeys, key, window_seconds):
        calls.append((script, numkeys, key, window_seconds))
        return 1

    monkeypatch.setattr(redis_client, "eval", fake_eval)

    from app.core.redis import check_rate_limit

    assert check_rate_limit("rate:test", 5, 60) is True
    assert len(calls) == 1

    script, numkeys, key, window_seconds = calls[0]
    assert "INCR" in script
    assert "EXPIRE" in script
    assert numkeys == 1
    assert key == "rate:test"
    assert window_seconds == 60


def test_rate_limit_rejects_attempt_over_limit(monkeypatch):
    monkeypatch.setattr(redis_client, "eval", lambda *args: 6)

    from app.core.redis import check_rate_limit

    assert check_rate_limit("rate:test", 5, 60) is False
