"""
Pydantic v2 schemas for Client request/response.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.domain.value_objects.client_status import ClientStatus


# ── Request schemas ──────────────────────────────────────────────────────

class CreateClientRequest(BaseModel):
    company: str = Field(..., min_length=2, max_length=255, description="Nombre de la empresa")
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    status: ClientStatus = ClientStatus.ACTIVO


class UpdateClientRequest(BaseModel):
    company: str | None = Field(None, min_length=2, max_length=255, description="Nombre de la empresa")
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    status: ClientStatus | None = None


# ── Response schemas ─────────────────────────────────────────────────────

class ClientResponse(BaseModel):
    id: UUID
    company: str
    email: str
    phone: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedClientResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int
    pages: int
