from sqlalchemy import ForeignKey, PrimaryKeyConstraint, Table, Column

from app.db.base import Base


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    PrimaryKeyConstraint("role_id", "permission_id"),
)