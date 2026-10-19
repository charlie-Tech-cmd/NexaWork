from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = "NexaWork"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    redis_url: str = "redis://localhost:6379/0"

    rate_limit_max_attempts: int = Field(default=5, gt=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)
    rate_limit_ip_max_attempts: int = Field(default=30, gt=0)
    rate_limit_ip_window_seconds: int = Field(default=60, gt=0)

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    jwt_secret_key: str
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, gt=0)

    password_reset_token_expire_minutes: int = Field(default=30, gt=0)
    password_reset_url: str = "http://localhost:3000/reset-password"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "nexawork"
    db_user: str = "postgres"
    db_password: str = "postgres"

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.environment.strip().lower() != "production":
            return self

        errors = []

        if self.db_host.strip().lower() in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            errors.append(
                "DB_HOST must not point to localhost in production"
            )

        if self.db_password.strip().lower() in {
            "",
            "postgres",
            "change-me",
        }:
            errors.append(
                "DB_PASSWORD must be explicitly configured in production"
            )

        if self.jwt_secret_key.strip().lower() in {
            "",
            "change-me",
            "secret",
            "your-secret-key",
            "replace-with-a-long-random-secret",
        }:
            errors.append(
                "JWT_SECRET_KEY must not use a placeholder in production"
            )

        if len(self.jwt_secret_key.encode("utf-8")) < 32:
            errors.append(
                "JWT_SECRET_KEY must be at least 32 bytes in production"
            )

        try:
            parsed_reset_url = urlsplit(self.password_reset_url.strip())
            reset_url_valid = (
                parsed_reset_url.scheme.lower() == "https"
                and bool(parsed_reset_url.hostname)
                and parsed_reset_url.username is None
                and parsed_reset_url.password is None
                and not parsed_reset_url.fragment
            )
            parsed_reset_url.port
        except ValueError:
            reset_url_valid = False

        if not reset_url_valid:
            errors.append(
                "PASSWORD_RESET_URL must be an absolute HTTPS URL "
                "without credentials or fragments in production"
            )

        origins = self.cors_origin_list
        if not origins:
            errors.append(
                "CORS_ORIGINS must contain at least one origin in production"
            )

        if any(
            origin == "*" or not origin.lower().startswith("https://")
            for origin in origins
        ):
            errors.append(
                "CORS_ORIGINS must contain explicit HTTPS origins in production"
            )

        if errors:
            raise ValueError("; ".join(errors))

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
