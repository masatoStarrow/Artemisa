"""
SQLAlchemy ORM model: users table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.connection import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<UserModel {self.email} ({self.role})>"
