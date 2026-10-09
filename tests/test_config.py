import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_production_settings(**overrides):
    values = {
        "environment": "production",
        "jwt_secret_key": "a-long-production-secret-value",
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


def test_development_defaults_remain_available():
    settings = Settings(
        _env_file=None,
        jwt_secret_key="test-secret-nexawork",
    )

    assert settings.environment == "development"
    assert settings.db_host == "localhost"
