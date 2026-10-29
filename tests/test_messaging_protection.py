import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError
from app.api.routes.messaging import protect_write
from app.core.config import settings, Settings


def test_message_rate_limit_and_outage_fail_closed(monkeypatch):
    monkeypatch.setattr(settings, "messaging_rate_limits_enabled", True)
    monkeypatch.setattr("app.core.redis.check_rate_limit", lambda *args: False)
    with pytest.raises(HTTPException) as limited: protect_write(1, 2, "send", 60)
    assert limited.value.status_code == 429
    assert limited.value.headers["Retry-After"] == "60"
    def unavailable(*args): raise RedisError("test unavailable")
    monkeypatch.setattr("app.core.redis.check_rate_limit", unavailable)
    with pytest.raises(HTTPException) as outage: protect_write(1, 2, "send", 60)
    assert outage.value.status_code == 503


def production(**changes):
    values = dict(
        _env_file=None,
        environment="production",
        jwt_secret_key="test-only-secret-with-over-thirty-two-bytes",
        db_host="db.example.invalid",
        db_password="test-only-password",
        password_reset_url="https://app.example.invalid/reset",
        cors_origins="https://app.example.invalid",
        allowed_hosts="api.example.invalid",
    )
    values.update(changes)
    return Settings(**values)


def test_production_cannot_enable_unscanned_or_unconfigured_files():
    with pytest.raises(ValueError): production(allow_unscanned_development_files=True)
    with pytest.raises(ValueError): production(attachments_enabled=True)
    assert production(
        attachments_enabled=True,
        persistent_local_storage=True,
        file_scan_host="private-scanner.invalid",
        messaging_rate_limits_enabled=True,
    ).attachments_enabled


def test_staging_cannot_use_development_scan_bypass():
    with pytest.raises(ValueError): Settings(
        _env_file=None,
        environment="staging",
        jwt_secret_key="test-only",
        allow_unscanned_development_files=True,
    )
