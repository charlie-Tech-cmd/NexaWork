from app.models.user import User


def can_activate_account(user: User) -> bool:
    return (
        not user.lifecycle_managed
        or (
            user.approval_status == "approved"
            and user.email_verified_at is not None
        )
    )


def can_authenticate_user(user: User) -> bool:
    return user.is_active and can_activate_account(user)
