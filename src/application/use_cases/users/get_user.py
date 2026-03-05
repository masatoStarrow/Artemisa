"""
Use case: Get a user by ID.
"""

from uuid import UUID

from src.domain.entities.user import User
from src.domain.exceptions import UserNotFoundError
from src.domain.ports.user_repository import UserRepository


class GetUser:
    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    async def execute(self, user_id: UUID) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user
