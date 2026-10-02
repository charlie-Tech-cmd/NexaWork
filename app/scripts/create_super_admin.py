from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security.password import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def create_super_admin(
    db: Session,
    *,
    email: str,
    full_name: str,
    password: str,
) -> User:
    normalized_email = email.strip().lower()
    normalized_name = full_name.strip()

    if not normalized_email:
        raise ValueError("Email is required.")

    if not normalized_name:
        raise ValueError("Full name is required.")

    if not password:
        raise ValueError("Password is required.")

    existing_user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if existing_user is not None:
        raise ValueError("A user with this email already exists.")

    super_admin = User(
        email=normalized_email,
        full_name=normalized_name,
        password_hash=hash_password(password),
        is_active=True,
        is_super_admin=True,
        organization_id=None,
    )

    db.add(super_admin)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Unable to create Super Admin. The email may already exist."
        ) from exc

    db.refresh(super_admin)
    return super_admin


def main() -> None:
    print("NexaWork Super Admin Provisioning")
    print("---------------------------------")

    full_name = input("Full name: ").strip()
    email = input("Email: ").strip()

    password = getpass("Password: ")
    password_confirmation = getpass("Confirm password: ")

    if password != password_confirmation:
        print("Error: passwords do not match.")
        raise SystemExit(1)

    db = SessionLocal()

    try:
        super_admin = create_super_admin(
            db,
            email=email,
            full_name=full_name,
            password=password,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc
    finally:
        db.close()

    print()
    print("Super Admin created successfully.")
    print(f"ID: {super_admin.id}")
    print(f"Email: {super_admin.email}")
    print(f"Name: {super_admin.full_name}")


if __name__ == "__main__":
    main()
