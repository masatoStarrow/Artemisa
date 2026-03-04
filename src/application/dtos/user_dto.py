"""
DTOs for User operations.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateUserDTO:
    email: str
    full_name: str
    role: str
    id: UUID | None = None


@dataclass
class UpdateUserDTO:
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


@dataclass
class UserResponseDTO:
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str
