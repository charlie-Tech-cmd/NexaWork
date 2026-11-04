import pytest
from pydantic import ValidationError

from app.schemas.organization import OrganizationOnboardingCreate
from app.schemas.user import AdminUserCreate, ResetPasswordRequest


@pytest.mark.parametrize(
    ("model", "payload", "field"),
    [
        (
            AdminUserCreate,
            {
                "email": "user@example.com",
                "password": "12345678",
                "confirm_password": "12345678",
                "full_name": "Test User",
            },
            "password",
        ),
        (
            AdminUserCreate,
            {
                "email": "user@example.com",
                "password": "12345678",
                "confirm_password": "12345678",
                "full_name": "Test User",
            },
            "confirm_password",
        ),
        (
            OrganizationOnboardingCreate,
            {
                "organization_name": "Test Organization",
                "organization_slug": "test-organization",
                "admin_email": "admin@example.com",
                "admin_password": "12345678",
                "admin_confirm_password": "12345678",
                "admin_full_name": "Test Admin",
            },
            "admin_password",
        ),
        (
            OrganizationOnboardingCreate,
            {
                "organization_name": "Test Organization",
                "organization_slug": "test-organization",
                "admin_email": "admin@example.com",
                "admin_password": "12345678",
                "admin_confirm_password": "12345678",
                "admin_full_name": "Test Admin",
            },
            "admin_confirm_password",
        ),
        (
            ResetPasswordRequest,
            {"token": "reset-token", "new_password": "12345678"},
            "new_password",
        ),
    ],
)
def test_password_schemas_reject_passwords_shorter_than_eight_characters(
    model,
    payload,
    field,
):
    invalid_payload = {**payload, field: "1234567"}

    with pytest.raises(ValidationError):
        model.model_validate(invalid_payload)


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            AdminUserCreate,
            {
                "email": "user@example.com",
                "password": "12345678",
                "confirm_password": "12345678",
                "full_name": "Test User",
            },
        ),
        (
            OrganizationOnboardingCreate,
            {
                "organization_name": "Test Organization",
                "organization_slug": "test-organization",
                "admin_email": "admin@example.com",
                "admin_password": "12345678",
                "admin_confirm_password": "12345678",
                "admin_full_name": "Test Admin",
            },
        ),
        (
            ResetPasswordRequest,
            {"token": "reset-token", "new_password": "12345678"},
        ),
    ],
)
def test_password_schemas_accept_eight_character_passwords(model, payload):
    model.model_validate(payload)
