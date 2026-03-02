"""
DTOs for Client operations.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateClientDTO:
    full_name: str
    email: str
    phone: str | None = None
    company: str | None = None
    status: str = "prospecto"
    assigned_agent_id: UUID | None = None
    notes: str | None = None


@dataclass
class UpdateClientDTO:
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    status: str | None = None
    notes: str | None = None


@dataclass
class ClientResponseDTO:
    id: UUID
    full_name: str
    email: str
    phone: str | None
    company: str | None
    status: str
    assigned_agent_id: UUID | None
    notes: str | None
    created_at: str
    updated_at: str
