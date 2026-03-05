"""
Use case: List clients with filters and pagination.
"""

from src.domain.entities.client import Client
from src.domain.ports.client_repository import ClientRepository


class ListClients:
    def __init__(self, client_repository: ClientRepository) -> None:
        self._repo = client_repository

    async def execute(
        self,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Client], int]:
        return await self._repo.list_clients(
            status=status,
            page=page,
            page_size=page_size,
        )
