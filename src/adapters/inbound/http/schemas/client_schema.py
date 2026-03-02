"""
Pydantic v2 schemas for Client request/response.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.domain.value_objects.client_status import ClientStatus


# ── Request schemas ──────────────────────────────────────────────────────

class CreateClientRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    company: str | None = Field(None, max_length=255)
    status: ClientStatus = ClientStatus.PROSPECTO
    assigned_agent_id: UUID | None = None
    notes: str | None = None


class UpdateClientRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    company: str | None = Field(None, max_length=255)
    status: ClientStatus | None = None
    notes: str | None = None


class AssignAgentRequest(BaseModel):
    agent_id: UUID


# ── Response schemas ─────────────────────────────────────────────────────

class ClientResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    phone: str | None
    company: str | None
    status: str
    assigned_agent_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedClientResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int
    pages: int
