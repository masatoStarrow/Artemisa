"""
Pydantic v2 schemas for User request/response.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.domain.value_objects.user_role import UserRole
from ..validators import validate_non_empty_name


# ── Request schemas ──────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    id: UUID | None = Field(None, description="UUID opcional para dual-write con el API Gateway. Si se omite, se genera automáticamente.")
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole
    
    @field_validator('full_name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return validate_non_empty_name(v)


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None
    
    @field_validator('full_name')
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_non_empty_name(v)
        return v


# ── Response schemas ─────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedUserResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SuccessResponse(BaseModel):
    success: bool = True
    data: dict | list | None = None
    message: str = "OK"


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
