"""
SQLAlchemy ORM model: clients table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.connection import Base


class ClientModel(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    company: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="prospecto", server_default=text("'prospecto'")
    )
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
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

    __table_args__ = (
        Index("idx_clients_assigned_agent", "assigned_agent_id"),
        Index("idx_clients_status", "status"),
        Index("idx_clients_company", "company"),
    )

    def __repr__(self) -> str:
        return f"<ClientModel {self.full_name} ({self.status})>"
