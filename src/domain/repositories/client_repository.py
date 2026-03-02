"""
ABC: ClientRepository — contract for client data access.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.client import Client


class ClientRepository(ABC):

    @abstractmethod
    async def get_by_id(self, client_id: UUID) -> Client | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Client | None:
        ...

    @abstractmethod
    async def list_clients(
        self,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Client], int]:
        """Return (items, total_count)."""
        ...

    @abstractmethod
    async def create(self, client: Client) -> Client:
        ...

    @abstractmethod
    async def update(self, client: Client) -> Client:
        ...

    @abstractmethod
    async def soft_delete(self, client_id: UUID) -> Client:
        ...
