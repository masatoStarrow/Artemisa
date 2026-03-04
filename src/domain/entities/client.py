"""
Domain entity: Client — pure Python dataclass, no framework imports.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Client:
    id: UUID
    company: str
    email: str
    phone: str | None = None
    status: str = "active"
    created_at: datetime | None = None
    updated_at: datetime | None = None
