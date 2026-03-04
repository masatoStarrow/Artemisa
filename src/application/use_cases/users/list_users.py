"""
Use case: List users with filters and pagination.
"""

from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository


class ListUsers:
    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    async def execute(
        self,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[User], int]:
        return await self._repo.list_users(
            role=role,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )
