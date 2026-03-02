"""
Domain entity: User — pure Python dataclass, no framework imports.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
