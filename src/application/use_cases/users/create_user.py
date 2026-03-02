"""
Use case: Create a new user.
"""

import uuid

from src.application.dtos.user_dto import CreateUserDTO
from src.domain.entities.user import User
from src.domain.exceptions import EmailAlreadyExistsError
from src.domain.repositories.user_repository import UserRepository


class CreateUser:
    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    async def execute(self, dto: CreateUserDTO) -> User:
        existing = await self._repo.get_by_email(dto.email)
        if existing is not None:
            raise EmailAlreadyExistsError("Ya existe un usuario con ese email")

        user = User(
            id=dto.id if dto.id else uuid.uuid4(),
            email=dto.email.strip().lower(),
            full_name=dto.full_name.strip(),
            role=dto.role,
            is_active=True,
        )
        return await self._repo.create(user)
