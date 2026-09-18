from sqlalchemy import Column, ForeignKey, PrimaryKeyConstraint, Table

from app.db.base import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    ),
    PrimaryKeyConstraint("user_id", "role_id"),
)