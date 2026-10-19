import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_production_settings(**overrides):
    values = {
        "environment": "production",
        "jwt_secret_key": "test-production-secret-with-enough-length",
        "db_host": "db.example.com",
        "db_password": "a-strong-database-password",
        "password_reset_url": "https://app.example.com/reset-password",
        "cors_origins": "https://app.example.com",
    }
    values.update(overrides)

    return Settings(_env_file=None, **values)


def test_valid_production_settings_are_accepted():
    settings = make_production_settings()

    assert settings.environment == "production"
    assert settings.cors_origin_list == ["https://app.example.com"]


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"db_host": "localhost"}, "DB_HOST"),
        ({"db_password": "postgres"}, "DB_PASSWORD"),
        ({"db_password": ""}, "DB_PASSWORD"),
        ({"jwt_secret_key": "change-me"}, "JWT_SECRET_KEY"),
        (
            {"password_reset_url": "http://localhost:3000/reset-password"},
            "PASSWORD_RESET_URL",
        ),
        ({"cors_origins": ""}, "CORS_ORIGINS"),
        ({"cors_origins": "http://app.example.com"}, "HTTPS"),
    ],
)
def test_unsafe_production_settings_are_rejected(override, message):
    with pytest.raises(ValidationError, match=message):
        make_production_settings(**override)


@pytest.mark.parametrize(
    "setting",
    [
        "rate_limit_max_attempts",
        "rate_limit_window_seconds",
        "rate_limit_ip_max_attempts",
        "rate_limit_ip_window_seconds",
    ],
)
@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_rate_limit_settings_are_rejected(setting, value):
    with pytest.raises(ValidationError):
        make_production_settings(**{setting: value})


@pytest.mark.parametrize(
    "setting",
    [
        "jwt_access_token_expire_minutes",
        "password_reset_token_expire_minutes",
    ],
)
@pytest.mark.parametrize("value", [0, -1])
def test_non_positive_token_lifetimes_are_rejected(setting, value):
    with pytest.raises(ValidationError):
        make_production_settings(**{setting: value})


def test_short_production_jwt_secret_is_rejected():
    with pytest.raises(ValidationError, match="32 bytes"):
        make_production_settings(jwt_secret_key="short-secret")


def test_unsupported_jwt_algorithm_is_rejected():
    with pytest.raises(ValidationError, match="HS256"):
        make_production_settings(jwt_algorithm="none")


def test_development_defaults_remain_available():
    settings = Settings(
        _env_file=None,
        jwt_secret_key="test-secret-nexawork",
    )

    assert settings.environment == "development"
    assert settings.db_host == "localhost"


@pytest.mark.parametrize(
    "password_reset_url",
    [
        "https://",
        "https:///reset-password",
        "https://user:password@app.example.com/reset-password",
        "https://app.example.com/reset-password#fragment",
    ],
)
def test_invalid_production_password_reset_urls_are_rejected(
    password_reset_url,
):
    with pytest.raises(ValidationError):
        make_production_settings(password_reset_url=password_reset_url)
