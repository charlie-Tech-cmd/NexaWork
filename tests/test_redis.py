from app.core.redis import redis_client


def test_redis_client_uses_configured_url():
    assert redis_client.connection_pool.connection_kwargs["host"] == "localhost"
    assert redis_client.connection_pool.connection_kwargs["port"] == 6379
    assert redis_client.connection_pool.connection_kwargs["db"] == 0
