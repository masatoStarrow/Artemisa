"""
DTOs for Client operations.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateClientDTO:
    company: str
    email: str
    phone: str | None = None
    status: str = "active"


@dataclass
class UpdateClientDTO:
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None

