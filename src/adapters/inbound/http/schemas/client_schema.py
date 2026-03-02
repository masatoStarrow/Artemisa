"""
Pydantic v2 schemas for Client request/response.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.domain.value_objects.client_status import ClientStatus
from ..validators import (
    validate_non_empty_name,
    validate_phone_format,
    validate_company_name,
    validate_notes_length,
)


# ── Request schemas ──────────────────────────────────────────────────────

class CreateClientRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    company: str | None = Field(None, max_length=255)
    status: ClientStatus = ClientStatus.PROSPECTO
    assigned_agent_id: UUID | None = None
    notes: str | None = None
    
    @field_validator('full_name')
    @classmethod  
    def validate_name(cls, v: str) -> str:
        return validate_non_empty_name(v)
        
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            return validate_phone_format(v)
        return v
        
    @field_validator('company')
    @classmethod
    def validate_company(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            return validate_company_name(v)
        return v
        
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_notes_length(v)
        return v


class UpdateClientRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    company: str | None = Field(None, max_length=255)
    status: ClientStatus | None = None
    notes: str | None = None
    
    @field_validator('full_name')
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_non_empty_name(v)
        return v
        
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            return validate_phone_format(v)
        return v
        
    @field_validator('company')
    @classmethod
    def validate_company(cls, v: str | None) -> str | None:
        if v is not None and v.strip():
            return validate_company_name(v)
        return v
        
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_notes_length(v)
        return v


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
