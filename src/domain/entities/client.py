"""
Domain entity: Client — pure Python dataclass, no framework imports.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Client:
    id: UUID
    full_name: str
    email: str
    phone: str | None = None
    company: str | None = None
    status: str = "prospecto"
    assigned_agent_id: UUID | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
