"""
ABC: UserRepository — contract for user data access.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.user import User


class UserRepository(ABC):

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def list_users(
        self,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[User], int]:
        """Return (items, total_count)."""
        ...

    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...

    @abstractmethod
    async def deactivate(self, user_id: UUID) -> User:
        ...
