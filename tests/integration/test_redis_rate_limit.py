import os
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
import redis

import app.core.redis as redis_module


@pytest.fixture
def redis_test_client(monkeypatch):
    redis_url = os.getenv("REDIS_TEST_URL")

    if not redis_url:
        pytest.skip("Set REDIS_TEST_URL to run Redis integration tests")

    client = redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    client.ping()
    monkeypatch.setattr(redis_module, "redis_client", client)

    try:
        yield client
    finally:
        client.close()


def test_rate_limit_is_atomic_under_concurrent_requests(redis_test_client):
    key = f"nexawork:test:rate-limit:{uuid4().hex}"

    try:
        with ThreadPoolExecutor(max_workers=50) as executor:
            results = list(
                executor.map(
                    lambda _: redis_module.check_rate_limit(key, 10, 60),
                    range(50),
                )
            )

        assert results.count(True) == 10
        assert results.count(False) == 40
        assert 0 < redis_test_client.ttl(key) <= 60
    finally:
        redis_test_client.delete(key)


def test_rate_limit_resets_after_expiry(redis_test_client):
    key = f"nexawork:test:rate-limit:{uuid4().hex}"

    try:
        assert redis_module.check_rate_limit(key, 1, 2) is True
        assert redis_module.check_rate_limit(key, 1, 2) is False

        deadline = time.monotonic() + 5
        while redis_test_client.exists(key) and time.monotonic() < deadline:
            time.sleep(0.05)

        assert redis_test_client.exists(key) == 0
        assert redis_module.check_rate_limit(key, 1, 2) is True
    finally:
        redis_test_client.delete(key)
