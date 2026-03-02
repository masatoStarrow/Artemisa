"""
Use case: Update a user's profile.
"""

from uuid import UUID

from src.application.dtos.user_dto import UpdateUserDTO
from src.domain.entities.user import User
from src.domain.exceptions import UserNotFoundError
from src.domain.repositories.user_repository import UserRepository


class UpdateUser:
    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    async def execute(self, user_id: UUID, dto: UpdateUserDTO) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()

        if dto.full_name is not None:
            user.full_name = dto.full_name.strip()
        if dto.role is not None:
            user.role = dto.role
        if dto.is_active is not None:
            user.is_active = dto.is_active

        return await self._repo.update(user)
